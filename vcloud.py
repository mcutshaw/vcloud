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
    def __init__(self, dict, vcloud):
        self.dict = dict
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
                    if task.status == 'running':
                        busy = True
                        break
            elif tasks is None or busy == False:
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

class Org(vObject):
    def __init__(self, dict, vcloud):
        super().__init__(dict, vcloud)

        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')

        self.id = self.href.split('/api/org/')[1]
        self.path = self.api+'/org/'+self.id

    def getUser(self, name, role=None):
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