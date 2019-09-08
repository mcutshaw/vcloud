#!/usr/bin/python3
import base64
from requests.auth import HTTPBasicAuth
from lxml import etree, objectify
import configparser
import requests
from datetime import datetime
import time

class vcloud:
    def __init__(self,config):
        self.config = config
        self.user = config['Main']['User']
        self.passwd = config['Main']['Password']
        self.host = config['Main']['Host']
        self.org = config['Main']['Org']

        self.api='https://%s/api' % self.host
        self.session_url='%s/sessions' % self.api
        self.query_url='%s/query' % self.api
        
        self.headers={'Accept': 'application/*+xml;version=30.0'}
        self._set_auth_token()

    def _set_auth_token(self):
        auth_str = '%s@%s:%s' % (self.user, self.org, self.passwd)
        auth=base64.b64encode(auth_str.encode()).decode('utf-8')
        self.headers['Authorization'] = 'Basic %s' % auth
        resp = requests.post(url=self.session_url, headers=self.headers)
        del self.headers['Authorization']
        try:
            self.headers['x-vcloud-authorization'] = resp.headers['x-vcloud-authorization']
        except KeyError:
            print("Authentication Error! Are you sure your credentials are correct?")
            exit()

    def getCatalog(self, name):
        resp = requests.get(url=self.api+'/catalogs/query?filter=name=='+ name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}CatalogRecord')
        return Catalog(result.attrib, self)
    
    def getVdc(self, name):
        resp = requests.get(url=self.api+'/query?type=orgVdc&filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}OrgVdcRecord')
        return orgVdc(result.attrib, self)
    
    def getOrg(self, name):
        resp = requests.get(url=self.api+'/admin/orgs/query?filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}OrgRecord')
        return Org(result.attrib, self)
    
    def getvApps(self, name):
        resp = requests.get(url=self.api+'/query?type=vApp&filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.findall('{*}VAppRecord')

        return [vApp(vapp.attrib, self) for vapp in result]

    def getEvents(self):
        l = []
        for x in range(1,9999):
            resp = requests.get(url=self.api+'/query?type=event&pageSize=128&page='+str(x), headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}EventRecord')
            if result == []:
                break
            l += [Event(event.attrib, self) for event in result]
        return l

    def getTasks(self):
        l = []
        for x in range(1,9999):
            resp = requests.get(url=self.api+'/query?type=task&pageSize=128&page='+str(x), headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}TaskRecord')
            if result == []:
                break
            l += [Task(task.attrib, self) for task in result]
        return l
    
    def genInstantiateVAppTemplateParams(self, name=None, deploy=False, powerOn=False, vAppHref=None):
        InstantiateVAppTemplateParams = etree.Element('InstantiateVAppTemplateParams')
        InstantiateVAppTemplateParams.set("xmlns","http://www.vmware.com/vcloud/v1.5")

        if name is None:
            date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S:%f")
            InstantiateVAppTemplateParams.set("name",date)
        else:
            InstantiateVAppTemplateParams.set("name",name)

        if deploy:
            InstantiateVAppTemplateParams.set("deploy","true")
        else:
            InstantiateVAppTemplateParams.set("deploy","false")

        if powerOn:
            InstantiateVAppTemplateParams.set("powerOn","true")
        else:
            InstantiateVAppTemplateParams.set("powerOn","false")
            
        InstantiationParams = etree.SubElement(InstantiateVAppTemplateParams, "InstantiationParams")

        if vAppHref is not None:
            Source = etree.SubElement(InstantiateVAppTemplateParams, "Source")
            Source.set("href", vAppHref)

        return etree.tostring(InstantiateVAppTemplateParams).decode('utf-8')

class vObject:
    def __init__(self, dictattrib, vcloud):
        
        self.dict = dict(dictattrib)
        self.addAttrib('name', 'name')
        self.addAttrib('href', 'href')

        self.api = vcloud.api
        self.headers = vcloud.headers
        self.vcloud = vcloud

    def addAttrib(self, key, name):
        if key in self.dict:
            setattr(self, name, self.dict[key])
        else:
            setattr(self, name, None)

    def getXML(self):
        resp = requests.get(url=self.path, headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        return xml_content

    def getSection(self, section):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        return tree.find('{*}'+section)
    
    def getTasks(self):
        tasks = self.getSection('Tasks')
        if tasks is not None:
            return [Task(task.attrib, self.vcloud) for task in tasks ]
        else:
            return None

    def waitOnReady(self, timeout=60, checkTime=5):
        for checks in range(int(timeout/checkTime)):
            busy = False
            tasks = self.getTasks()
            if tasks is not None:
                for task in tasks:
                    if task.status == 'running' or task.status == 'queued':
                        busy = True
                        break
            if tasks is None or busy == False:
                return True
            time.sleep(checkTime)

    def delete(self, timeout=60, checkTime=5):
        self.waitOnReady(timeout=timeout, checkTime=checkTime)
        resp = requests.delete(url=self.path, headers=self.headers)
        return resp.status_code

    def changeOwner(self, user, timeout=60, checkTime=5):
        self.waitOnReady(timeout=timeout, checkTime=checkTime)
        params=self._generateOwnerParams(user)
        resp = requests.put(url=self.href+'/owner', headers=self.headers, data=params)
        if 'Error' in resp.text:
            print('Error:',tree.attrib['message'])
            return None
        return self

    def _generateOwnerParams(self, user):
        Owner = etree.Element('Owner')
        Owner.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        User = etree.SubElement(Owner, "User")
        User.set("href",user.href)
        User.set("type","application/vnd.vmware.admin.user+xml")
        return etree.tostring(Owner).decode('utf-8')

    def _generateUserParams(self, name, role):
        User = etree.Element('User')
        User.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        User.set("name", name)
            
        IsEnabled = etree.SubElement(User, "IsEnabled")
        IsEnabled.text = "true"
        IsExternal = etree.SubElement(User, "IsExternal")
        IsExternal.text = "true"
        Role = etree.SubElement(User, "Role")
        Role.set("href",role.path)
        return etree.tostring(User).decode('utf-8')

    def _action(self, actionPath, requestType='POST', data=None, timeout=60, checkTime=5):
        self.waitOnReady(timeout=timeout, checkTime=checkTime)
        if requestType.upper() == 'POST':
            resp = requests.post(url=actionPath, headers=self.headers, data=data)
        if requestType.upper() == 'GET':
            resp = requests.get(url=actionPath, headers=self.headers)
        if requestType.upper() == 'DELETE':
            resp = requests.delete(url=actionPath, headers=self.headers)
        if requestType.upper() == 'PUT':
            resp = requests.put(url=actionPath, headers=self.headers, data=data)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        if 'Error' in tree.tag:
            print('Error:',tree.attrib['message'])
            return None
        return tree

class VAppTemplate(vObject):
    def __init__(self, dict, vcloud):

        super().__init__(dict, vcloud)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('numberOfVMs', 'VMNum')

        self.id = self.href.split('/api/vAppTemplate/')[1]
        self.path = self.api+'/vAppTemplate/'+self.id

    def renew(self, leaseSecs=7776000):
        
        resp = requests.get(url=self.path + '/leaseSettingsSection', headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)

        tree.find('{*}StorageLeaseInSeconds').text = str(leaseSecs)
        leaseSection = etree.tostring(tree, encoding="utf-8", method="xml").decode('utf-8')

        resp = requests.put(url=self.path + '/leaseSettingsSection', data=leaseSection, headers=self.headers)

    def GetVMTemplates(self):
        resp = requests.get(url=self.api+'/vAppTemplate/'+self.id, headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        children = tree.find('{*}Children')
        vms = children.findall('{*}Vm')
        return [VMTemplate({**self.dict, **template.attrib}, self.vcloud) for template in vms]

    def deploy(self, vdc, name=None):
        params = self.vcloud.genInstantiateVAppTemplateParams(vAppHref=self.path,name=name)
        resp = requests.post(url=self.vcloud.api + '/vdc/'+vdc.id+'/action/instantiateVAppTemplate', headers=self.headers, data=params)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        
        if 'Error' in tree.tag:
            print('Error:',tree.attrib['message'])
            return None
        return vApp(tree.attrib, self.vcloud)

class orgVdc(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('orgName', 'org')
        self.addAttrib('numberOfVMs', 'numberOfVMs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')

        self.id = self.href.split('/api/vdc/')[1]
        self.path = self.api+'/vdc/'+self.id

class Task(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('operationName', 'operationName')
        self.addAttrib('operationFull', 'operationFull')
        self.addAttrib('ownerName', 'ownerName')

        self.addAttrib('endDate', 'endDate')
        if self.endDate is not None:
            self.endDate = datetime.strptime(self.endDate, '%Y-%m-%dT%H:%M:%S.%f%z')

        self.addAttrib('startDate', 'startDate')
        if self.startDate is not None:
            self.startDate = datetime.strptime(self.startDate, '%Y-%m-%dT%H:%M:%S.%f%z')

        self.addAttrib('objectType', 'objectType')
        self.addAttrib('objectName', 'objectName')
        self.addAttrib('object', 'object')

        self.addAttrib('status', 'status')

        self.id = self.href.split('/api/task/')[1]
        self.path = self.api+'/task/'+self.id

class VMTemplate(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)
        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')

        self.id = self.href.split('/api/vAppTemplate/vm-')[1]
        self.path = self.api+'/vAppTemplate/vm-'+self.id

class vApp(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('owner', 'owner')

        self.id = self.href.split('/api/vApp/vapp-')[1]
        self.path = self.api+'/vApp/vapp-'+self.id

    def powerOn(self, timeout=60, checkTime=5):
        tree = self._action(self.path + '/power/action/powerOn')
        if tree is None:
            return None
        return self

    def _powerOff(self, timeout=60, checkTime=5): #Hard, method for powering off without undeploying
        tree = self._action(self.path + '/power/action/powerOff')
        if tree is None:
            return None
        return self

    def powerOff(self, timeout=60, checkTime=5): #Hard, with undeploy
        result = self.undeploy(timeout=timeout, checkTime=checkTime, powerOffType='powerOff')
        if result is None:
            return None
        return self

    def _shutdown(self, timeout=60, checkTime=5): #Soft, method for powering off without undeploying
        tree = self._action(self.path + '/power/action/shutdown')
        if tree is None:
            return None
        return self
    
    def shutdown(self, timeout=60, checkTime=5): #Soft, with undeploy
        result = self.undeploy(timeout=timeout, checkTime=checkTime, powerOffType='shutdown')
        print('Shutdown does not appear to work if all vms do not have vmware tools, use powerOff instead')
        if result is None:
            return None
        return self

    def _suspend(self, timeout=60, checkTime=5): #Method for suspending without undeploying
        tree = self.undeploy()
        if tree is None:
            return None
        return self

    def suspend(self, timeout=60, checkTime=5): #with undeploy
        result = self.undeploy(timeout=timeout, checkTime=checkTime, powerOffType='suspend')
        if result is None:
            return None
        return self

    def reset(self, timeout=60, checkTime=5): # hard
        tree = self._action(self.path + '/power/action/reset')
        if tree is None:
            return None
        return self

    def reboot(self, timeout=60, checkTime=5):
        tree = self._action(self.path + '/power/action/reboot')
        if tree is None:
            return None
        return self

    def unsuspend(self, timeout=60, checkTime=5):
        tree = self._action(self.path + '/action/discardSuspendedState')
        if tree is None:
            return None
        return self
        
    def genUndeployParams(self, powerOffType='default'):
        UndeployVAppParams = etree.Element('UndeployVAppParams')
        UndeployVAppParams.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        UndeployPowerAction = etree.SubElement(UndeployVAppParams, "UndeployPowerAction")
        UndeployPowerAction.text = powerOffType
        return etree.tostring(UndeployVAppParams).decode('utf-8')

    def undeploy(self, timeout=60, checkTime=5, powerOffType='default'):
        params = self.genUndeployParams(powerOffType=powerOffType)
        tree = self._action(self.path +'/action/undeploy', data=params)
        if tree is None:
            return None
        return self
        
    def _genSnapshotParams(self):
        CreateSnapshotParams = etree.Element('CreateSnapshotParams')
        CreateSnapshotParams.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        Description = etree.SubElement(CreateSnapshotParams, "Description")
        Description.text = "Snapshot"
        return etree.tostring(CreateSnapshotParams).decode('utf-8')

    def snapshot(self):
        params = self._genSnapshotParams()
        tree = self._action(self.path +'/action/createSnapshot', data=params)
        if tree is None:
            return None
        return self

    def revert(self):
        tree = self._action(self.path +'/action/revertToCurrentSnapshot')
        if tree is None:
            return None
        return self

class User(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')

        self.id = self.href.split('/api/admin/user/')[1]
        self.path = self.api+'/admin/user/'+self.id

class Role(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')
        self.id = self.href.split('/api/admin/role/')[1]
        self.path = self.api+'/admin/role/'+self.id

class Event(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('entityName', 'entityName')
        self.addAttrib('entityType', 'entityType')
        self.addAttrib('eventStatus', 'eventStatus')
        self.addAttrib('eventType', 'eventType')

        self.addAttrib('entityHref', 'entity')

        self.addAttrib('userName', 'userName')
        self.addAttrib('eventStatus', 'eventStatus')
        self.addAttrib('description', 'description')
        self.addAttrib('eventId', 'id')
        self.addAttrib('timeStamp', 'timeStamp')
        #self.path = self.api+'/admin/'+self.id

class Org(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')

        self.id = self.href.split('/api/org/')[1]
        self.path = self.api+'/org/'+self.id

    def getUser(self, name, role=None):
        name = name.lower()
        resp = requests.get(url=self.api+'/query?type=user&filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}UserRecord')
        if result is None and role is not None:
            return self.importUser(name, role)
        elif result is not None:
            return User(result.attrib, self)
        else:
            return None


    def getRole(self, name):
        resp = requests.get(url=self.api+'/query?type=role&filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}RoleRecord')
        if result is None:
            return None
        return Role(result.attrib, self)

    def importUser(self, name, role):
        params = self._generateUserParams(name, role)
        resp = requests.post(url=self.api +'/admin/org/'+self.id+'/users', headers=self.headers, data=params)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        if 'Error' in tree.tag:
            print('Error:',tree.attrib['message'])
            return None
        return User(tree.attrib, self.vcloud)

class Catalog(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('orgName', 'org')
        self.id = self.href.split('/api/catalog/')[1]
        self.path = self.api+'/catalog/'+self.id
        
    def getTemplates(self, filter='*'):
        resp = requests.get(url=self.api+'/vAppTemplates/query?pageSize=128&filter=(name=='+ filter+')',headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        results = tree.findall('{*}VAppTemplateRecord')
        return [VAppTemplate(template.attrib, self.vcloud) for template in results]