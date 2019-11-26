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

        self.api=f'https://{self.host}/api'
        self.session_url=f'{self.api}/sessions'
        
        self.headers={'Accept': 'application/*+xml;version=30.0'}
        self._set_auth_token()

    def _set_auth_token(self):
        auth_str = '%s@%s:%s' % (self.user, self.org, self.passwd)
        auth=base64.b64encode(auth_str.encode()).decode('utf-8')
        self.headers['Authorization'] = f'Basic {auth}'
        resp = requests.post(url=self.session_url, headers=self.headers)
        del self.headers['Authorization']
        try:
            self.headers['x-vcloud-authorization'] = resp.headers['x-vcloud-authorization']
        except KeyError:
            print("Authentication Error! Are you sure your credentials are correct?")
            exit()

    def checkAuth(self, username, password):
        headers={'Accept': 'application/*+xml;version=30.0'}

        auth_str = f'{username}@{self.org}:{password}'
        auth=base64.b64encode(auth_str.encode()).decode('utf-8')
        headers['Authorization'] = f'Basic {auth}'
        resp = requests.post(url=self.session_url, headers=headers)
        del username
        del password
        del headers['Authorization']
        try:
            del resp.headers['x-vcloud-authorization']
        except KeyError:
            return False
        return True


    def getCatalog(self, name):
        resp = requests.get(url=self.api+'/catalogs/query?filter=name=='+ name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}CatalogRecord')
        return Catalog(result, self)
    
    def getVdc(self, name):
        resp = requests.get(url=self.api+'/query?type=orgVdc&filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}OrgVdcRecord')
        return orgVdc(result, self)

    def getOrgNetworks(self, name):
        l = []
        for x in range(1,9999):
            resp = requests.get(url=self.api+'/query?type=orgNetwork&filter=name=='+name+'&pageSize=128&page='+str(x),headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}OrgNetworkRecord')
            if result == []:
                    break
            l += [network(Network, self) for Network in result]
        return l
    
    def getOrg(self, name):
        resp = requests.get(url=self.api+'/admin/orgs/query?filter=name=='+name,headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}OrgRecord')
        return Org(result, self)
    
    def getvApps(self, name):
        l = []
        for x in range(1,9999):
            resp = requests.get(url=self.api+'/query?type=vApp&filter=name=='+name+'&pageSize=128&page='+str(x),headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}VAppRecord')
            if result == []:
                    break
            l += [vApp(vapp, self) for vapp in result]
        return l

    def getMedia(self, filter='*', vdc=None):
        if vdc is not None:
            resp = requests.get(url=self.api+'/query?pageSize=128&type=media&filter=(name=='+ filter+';vdc=='+vdc.href+')',headers=self.headers)
        else:
            resp = requests.get(url=self.api+'/query?pageSize=128&type=media&filter=(name=='+ filter+')',headers=self.headers)

        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        results = tree.findall('{*}MediaRecord')
        return [Media(media, self) for media in results]
    
    def getVMs(self, name):
        l = []
        for x in range(1,9999):
            resp = requests.get(url=self.api+'/query?type=vm&filter=isVAppTemplate==false;name=='+name+'&pageSize=128&page='+str(x),headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}VMRecord')
            if result == []:
                    break
            l += [VM(vm, self) for vm in result]
        return l

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
            l += [Event(event, self) for event in result]
        return l

    def getTasks(self, name, object=None):
        l = []
        for x in range(1,9999):
            if object is not None:
                resp = requests.get(url=self.api+'/query?type=task&filter=name=='+name+';object=='+object+'&pageSize=128&page='+str(x), headers=self.headers)
            else:
                resp = requests.get(url=self.api+'/query?type=task&filter=name=='+name+'&pageSize=128&page='+str(x), headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            result = tree.findall('{*}TaskRecord')
            if result == []:
                break
            l += [Task(task, self) for task in result]
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
        
        self.dict = dict(dictattrib.attrib)

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
        resp = requests.get(url=self.href, headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        return xml_content

    
    def genAttrib(self):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        self.dict = dict(tree.attrib)
        for key in self.dict:
            self.addAttrib(key, key)
        
        for child in tree:
            string = child.tag
            string = string.split('}')[1]
            setattr(self, string, d)
            d = dict(child.attrib)


    def getSection(self, section):
        tree = self.getETree()
        return tree.find('{*}'+section)

    def getETree(self):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        return tree
    
    def getTasks(self):
        tasks = self.getSection('Tasks')
        if tasks is not None:
            return [Task(task, self.vcloud) for task in tasks ]
        else:
            return None

    def waitOnReady(self, timeout=60, checkTime=5):
        for _ in range(int(timeout/checkTime)):
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
        resp = requests.delete(url=self.href, headers=self.headers)
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


    def addUsers(self, users=None, timeout=60, checkTime=5, perms="ReadOnly"):
            resp = requests.get(url=self.href+'/controlAccess', headers=self.headers)
            xml_content = resp.text.encode('utf-8')
            parser = etree.XMLParser(ns_clean=True, recover=True)
            tree = etree.fromstring(bytes(xml_content), parser=parser)
            AccessSettings = tree.find('{*}AccessSettings')
            if AccessSettings == None:
                AccessSettings = etree.SubElement(tree, "AccessSettings")
            self.waitOnReady(timeout=timeout, checkTime=checkTime)
            if users is not None:
                for user in users:
                    acl = self._generateACLParams(user, perms=perms)
                    AccessSettings.append(acl)
            params = etree.tostring(tree)
            tree = self._action(self.href+'/action/controlAccess', data=params)

    def _generateACLParams(self, user, perms="ReadOnly"):
        AccessSetting = etree.Element('AccessSetting')

        Subject = etree.SubElement(AccessSetting, "Subject")
        Subject.set("href", user.href)
        Subject.set("name", user.name)
        Subject.set("type", "application/vnd.vmware.admin.user+xml")

        AccessLevel = etree.SubElement(AccessSetting, "AccessLevel")
        AccessLevel.text = perms

        return AccessSetting

    def _generateUserParams(self, name, role):
        User = etree.Element('User')
        User.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        User.set("name", name)
            
        IsEnabled = etree.SubElement(User, "IsEnabled")
        IsEnabled.text = "true"
        IsExternal = etree.SubElement(User, "IsExternal")
        IsExternal.text = "true"
        Role = etree.SubElement(User, "Role")
        Role.set("href",role.href)
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
            raise Exception(tree.attrib['message'])
        return tree

    def checkSnapshotExists(self):
        if self.getSection('SnapshotSection').find('{*}Snapshot') is None:
            return False
        else:
            return True

    def _genRenameParams(self, newName, description=None):
        CatalogItem = etree.Element('CatalogItem')
        CatalogItem.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        CatalogItem.set("name",f"{newName}")
        if description is None:
            description = ''
        Description = etree.SubElement(CatalogItem, "Description")
        Description.text = description

        Entity = etree.SubElement(CatalogItem, "Entity")
        Entity.set("href", self.href)
        return etree.tostring(CatalogItem).decode('utf-8')

    def rename(self, newName, timeout=60, checkTime=5, description=None):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        catalogRel = tree.find("{*}Link[@rel='catalogItem']")
        href = catalogRel.attrib['href']
        params = self._genRenameParams( newName, description=None)
        tree = self._action(href, requestType='PUT', data=params)
        if tree is None:
            return None
        return self

        

class alive:
    def resolveStatus(self):
        p = {'-1':'FAILED_CREATION',
        '0':'UNRESOLVED',
        '1':'RESOLVED',
        '2':'DEPLOYED',
        '3':'SUSPENDED',
        '4':'POWERED_ON',
        '5':'WAITING_FOR_INPUT',
        '6':'UNKNOWN',
        '7':'UNRECOGNIZED',
        '8':'POWERED_OFF',
        '9':'INCONSISTENT_STATE',
        '10':'MIXED',
        '11':'DESCRIPTOR_PENDING',
        '12':'COPYING_CONTENTS',
        '13':'DISK_CONTENTS_PENDING',
        '14':'QUARANTINED',
        '15':'QUARANTINE_EXPIRED',
        '16':'REJECTED',
        '17':'TRANSFER_TIMEOUT',
        '18':'VAPP_UNDEPLOYED',
        '19':'VAPP_PARTIALLY_DEPLOYED'}
        if str(self.status) in p.keys():
            self.status = p[str(self.status)]

    def powerOn(self, timeout=60, checkTime=5):
        tree = self._action(self.href + '/power/action/powerOn')
        if tree is None:
            return None
        return self

    def _powerOff(self, timeout=60, checkTime=5): #Hard, method for powering off without undeploying
        tree = self._action(self.href + '/power/action/powerOff')
        if tree is None:
            return None
        return self

    def powerOff(self, timeout=60, checkTime=5): #Hard, with undeploy
        result = self.undeploy(timeout=timeout, checkTime=checkTime, powerOffType='powerOff')
        if result is None:
            return None
        return self

    def _shutdown(self, timeout=60, checkTime=5): #Soft, method for powering off without undeploying
        tree = self._action(self.href + '/power/action/shutdown')
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
        tree = self._action(self.href + '/power/action/reset')
        if tree is None:
            return None
        return self

    def reboot(self, timeout=60, checkTime=5):
        tree = self._action(self.href + '/power/action/reboot')
        if tree is None:
            return None
        return self

    def unsuspend(self, timeout=60, checkTime=5):
        tree = self._action(self.href + '/action/discardSuspendedState')
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
        tree = self._action(self.href +'/action/undeploy', data=params)
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
        tree = self._action(self.href +'/action/createSnapshot', data=params)
        if tree is None:
            return None
        return self

    def revert(self):
        
        tree = self._action(self.href +'/action/revertToCurrentSnapshot')
        if tree is None:
            return None
        return self

class VAppTemplate(vObject):
    def __init__(self, dict, vcloud):

        super().__init__(dict, vcloud)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('numberOfVMs', 'numberOfVMs')
        self.id = self.href.split('/api/vAppTemplate/')[1]

    def renew(self, leaseSecs=7776000):
        
        resp = requests.get(url=self.href + '/leaseSettingsSection', headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)

        tree.find('{*}StorageLeaseInSeconds').text = str(leaseSecs)
        leaseSection = etree.tostring(tree, encoding="utf-8", method="xml").decode('utf-8')

        resp = requests.put(url=self.href + '/leaseSettingsSection', data=leaseSection, headers=self.headers)

    def getVMTemplates(self):
        resp = requests.get(url=self.api+'/vAppTemplate/'+self.id, headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        children = tree.find('{*}Children')
        vms = children.findall('{*}Vm')
        return [VMTemplate({**self.dict, **template}, self.vcloud) for template in vms]

    def deploy(self, vdc, name=None):
        params = self.vcloud.genInstantiateVAppTemplateParams(vAppHref=self.href,name=name)
        resp = requests.post(url=self.vcloud.api + '/vdc/'+vdc.id+'/action/instantiateVAppTemplate', headers=self.headers, data=params)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        
        if 'Error' in tree.tag:
            print('Error:',tree.attrib['message'])
            return None
        return vApp(tree, self.vcloud)

class orgVdc(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('orgName', 'org')
        self.addAttrib('numberOfVMs', 'numberOfVMs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')

        self.id = self.href.split('/api/vdc/')[1]

class network(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('org', 'org')
        self.addAttrib('type', 'type')

        self.id = self.href.split('/api/network/')[1]

    def update(self):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        return network(tree, self.vcloud)
         

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

class VMTemplate(vObject, alive):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)
        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')

        self.id = self.href.split('/api/vAppTemplate/vm-')[1]

class VM(vObject, alive):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('owner', 'owner')
        self.addAttrib('container', 'container')
        self.addAttrib('status', 'status')
        self.id = self.href.split('/api/vApp/vm-')[1]

        self.resolveStatus()

    def lastOpened(self):
        tasks = self.vcloud.getTasks('jobAcquireScreenTicket', object=self.href)
        tasks.sort(key=lambda x: x.startDate)
        if tasks is None or tasks == []:
            return None
        else:
            return(tasks[0].startDate)

    def checkGuestCustomization(self):
        string = self.getSection('GuestCustomizationSection').find('{*}Enabled').text
        if string == 'true':
            return True
        else:
            return False
        

class vApp(vObject, alive):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('owner', 'owner')
        self.addAttrib('status', 'status')
        self.resolveStatus()

        self.id = self.href.split('/api/vApp/vapp-')[1]

    def capture(self, catalog, name=None, descriptionText=''):
        resp = self._action(catalog.href+'/action/captureVApp', data=self._generateCaptureParams(name, descriptionText))
        if resp is None:
            return None
        else:
            return Task(resp, self.vcloud)

    def _generateCaptureParams(self, name, descriptionText):
        CaptureVAppParams = etree.Element('CaptureVAppParams')
        CaptureVAppParams.set("xmlns","http://www.vmware.com/vcloud/v1.5")

        if name is None:
            CaptureVAppParams.set("name",self.name)

        else:
            CaptureVAppParams.set("name",name)

        Description = etree.SubElement(CaptureVAppParams, "Description")
        Description.text = descriptionText

        Source = etree.SubElement(CaptureVAppParams, "Source")
        Source.set('href', self.href)

        CustomizationSection = etree.SubElement(CaptureVAppParams, "CustomizationSection")
        Info = etree.SubElement(CustomizationSection, "{http://schemas.dmtf.org/ovf/envelope/1}Info")
        CustomizeOnInstantiate = etree.SubElement(CustomizationSection, "CustomizeOnInstantiate")
        CustomizeOnInstantiate.text = 'true'

        return etree.tostring(CaptureVAppParams).decode('utf-8')

    def getVMs(self):
        resp = requests.get(url=self.href, headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        children = tree.find('{*}Children')
        vms = children.findall('{*}Vm')
        l = []
        for vm in vms:
            l.append(VM(vm, self.vcloud))
        return l
    
    def lastOpened(self):
        vms = self.getVMs()
        date = None
        for vm in vms: 
            vmDate = vm.lastOpened() 
            if vmDate is None:
                continue
            elif date is None or vmDate > date:
                date = vmDate
        return date

    def checkGuestCustomization(self):
        vms = self.getVMs()
        for vm in vms: 
            if vm.checkGuestCustomization():
                return True
        return False
    

class User(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')

        self.id = self.href.split('/api/admin/user/')[1]

class Role(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')
        self.id = self.href.split('/api/admin/role/')[1]

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

class Org(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')

        self.id = self.href.split('/api/org/')[1]

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
            return User(result, self)
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
        return Role(result, self)

    def importUser(self, name, role):
        params = self._generateUserParams(name, role)
        resp = requests.post(url=self.api +'/admin/org/'+self.id+'/users', headers=self.headers, data=params)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        if 'Error' in tree.tag:
            print('Error:',tree.attrib['message'])
            return None
        return User(tree, self.vcloud)

class Catalog(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('orgName', 'org')
        self.id = self.href.split('/api/catalog/')[1]
        
    def getTemplates(self, filter='*', vdc=None):
        if vdc is not None:
            resp = requests.get(url=self.api+'/vAppTemplates/query?pageSize=128&filter=(name=='+ filter+';vdc=='+vdc.href+')',headers=self.headers)
        else:
            resp = requests.get(url=self.api+'/vAppTemplates/query?pageSize=128&filter=(name=='+ filter+')',headers=self.headers)
        
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        results = tree.findall('{*}VAppTemplateRecord')
        return [VAppTemplate(template, self.vcloud) for template in results]

class Media(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('catalog', 'catalogHref')
        self.addAttrib('owner', 'ownerHref')
        self.addAttrib('vdcName', 'vdcName')
        self.id = self.href.split('/media/')[1]
    
    
    def _generateCloneParams(self, name, deleteSource=False, description="Empty"):
        CloneMediaParams = etree.Element('CloneMediaParams')
        CloneMediaParams.set("xmlns","http://www.vmware.com/vcloud/v1.5")
        CloneMediaParams.set("name", name)
            
        Description = etree.SubElement(CloneMediaParams, "Description")
        Description.text = description

        Source = etree.SubElement(CloneMediaParams, "Source")
        Source.set("href",self.href)
        Source.set("id",self.id)
        Source.set("type","media")
        Source.set("name",self.name)

        IsSourceDelete = etree.SubElement(CloneMediaParams, "IsSourceDelete")
        if deleteSource:
            IsSourceDelete.text = "true"
        else:
            IsSourceDelete.text = "false"
        return etree.tostring(CloneMediaParams).decode('utf-8')

    def clone(self, name, vdc, deleteSource=False, description="Empty"):
        resp = self._action(f'{vdc.href}/action/cloneMedia', data=self._generateCloneParams(name, deleteSource=deleteSource, description=description))
        print(resp.text)
        if resp is None:
            return None
        else:
            return Media(resp, self.vcloud)