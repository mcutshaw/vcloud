#!/usr/bin/python3
import base64
import time
from datetime import datetime
from typing import List

import requests
from lxml import etree

from util import treeify_xml


class vObject:
    def __init__(self, dictattrib, vcloud_obj):
        self.dict = dict(dictattrib.attrib)

        self.name = self.dict.get("name", None)
        self.href = self.dict.get("href", None)

        self.api = vcloud_obj.api
        self.headers = vcloud_obj.headers
        self.vcloud = vcloud_obj

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
        return tree.find('{*}' + section)

    def getETree(self):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        return tree

    def waitOnReady(self, timeout: int = 300, check_time: int = 5):
        for _ in range(int(timeout / check_time)):
            busy = False
            tasks = self.vcloud.getTasks(object_href=self.href)
            if tasks is not None:
                for task in tasks:
                    if task.status == 'running' or task.status == 'queued':
                        busy = True
                        break
            if tasks is None or busy is False:
                return True
            time.sleep(check_time)
        print(" == Timeout exceeded! == ")
        return False

    def delete(self, timeout: int = 300, check_time: int = 5):
        self.waitOnReady(timeout=timeout, check_time=check_time)
        resp = requests.delete(url=self.href, headers=self.headers)
        return resp.status_code

    def changeOwner(self, user, timeout: int = 300, check_time: int = 5):
        self.waitOnReady(timeout=timeout, check_time=check_time)
        params = self._generateOwnerParams(user)
        resp = requests.put(url=self.href + '/owner', headers=self.headers, data=params)
        if 'Error' in resp.text:
            print('Error:', resp.text)
            return None
        return self

    def _generateOwnerParams(self, user):
        Owner = etree.Element('Owner')
        Owner.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        User = etree.SubElement(Owner, "User")
        User.set("href", user.href)
        User.set("type", "application/vnd.vmware.admin.user+xml")
        return etree.tostring(Owner).decode('utf-8')

    def addUsers(self, users=None, timeout: int = 300, check_time: int = 5, perms: str = "ReadOnly"):
        """
        Add users to vapp
        :param users:
        :param timeout:
        :param check_time:
        :param perms: FullControl, Change, ReadOnly
        :return:
        """
        resp = requests.get(url=self.href + '/controlAccess', headers=self.headers)
        tree = treeify_xml(resp)
        access_settings = tree.find('{*}AccessSettings')
        if access_settings is None:
            access_settings = etree.SubElement(tree, "AccessSettings")
        self.waitOnReady(timeout=timeout, check_time=check_time)
        if users is not None:
            for user in users:
                acl = self._generateACLParams(user, perms=perms)
                access_settings.append(acl)
        params = etree.tostring(tree)
        tree = self._action(self.href + '/action/controlAccess', data=params, timeout=timeout, checkTime=check_time)

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
        User.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        User.set("name", name)

        IsEnabled = etree.SubElement(User, "IsEnabled")
        IsEnabled.text = "true"
        IsExternal = etree.SubElement(User, "IsExternal")
        IsExternal.text = "true"
        Role = etree.SubElement(User, "Role")
        Role.set("href", role.href)
        return etree.tostring(User).decode('utf-8')

    def _action(self, actionPath, requestType='POST', data=None, timeout: int = 300, checkTime: int = 5):
        self.waitOnReady(timeout=timeout, check_time=checkTime)
        if requestType.upper() == 'POST':
            resp = requests.post(url=actionPath, headers=self.headers, data=data)
        if requestType.upper() == 'GET':
            resp = requests.get(url=actionPath, headers=self.headers)
        if requestType.upper() == 'DELETE':
            resp = requests.delete(url=actionPath, headers=self.headers)
        if requestType.upper() == 'PUT':
            resp = requests.put(url=actionPath, headers=self.headers, data=data)
        tree = treeify_xml(resp)
        if 'Error' in tree.tag:
            print('Error:', tree.attrib['message'])
            raise Exception(tree.attrib['message'])
        return tree

    def checkSnapshotExists(self):
        if self.getSection('SnapshotSection').find('{*}Snapshot') is None:
            return False
        else:
            return True

    def putCustomXML(self, path: str, text: str, timeout: int = 300, check_time: int = 5):
        self.waitOnReady(timeout=timeout, check_time=check_time)
        response = requests.put(self.href + path, data=text.encode("utf-8"), headers=self.vcloud.headers)
        print(response.content.decode("UTF-8"))

    def postCustomXML(self, path: str, text: str, timeout: int = 300, check_time: int = 5):
        self.waitOnReady(timeout=timeout, check_time=check_time)
        response = requests.post(self.href + path, data=text.encode("utf-8"), headers=self.vcloud.headers)
        print(response.content.decode("UTF-8"))

    def _genRenameParams(self, newName, description=None):
        CatalogItem = etree.Element('CatalogItem')
        CatalogItem.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        CatalogItem.set("name", f"{newName}")
        if description is None:
            description = ''
        Description = etree.SubElement(CatalogItem, "Description")
        Description.text = description

        Entity = etree.SubElement(CatalogItem, "Entity")
        Entity.set("href", self.href)
        return etree.tostring(CatalogItem).decode('utf-8')

    def rename(self, newName, timeout: int = 300, checkTime: int = 5, description=None):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        catalogRel = tree.find("{*}Link[@rel='catalogItem']")
        href = catalogRel.attrib['href']
        params = self._genRenameParams(newName, description=None)
        tree = self._action(href, requestType='PUT', data=params, timeout=timeout, checkTime=checkTime)
        if tree is None:
            return None
        return self


class alive(vObject):
    def resolveStatus(self):
        p = {'-1': 'FAILED_CREATION',
             '0': 'UNRESOLVED',
             '1': 'RESOLVED',
             '2': 'DEPLOYED',
             '3': 'SUSPENDED',
             '4': 'POWERED_ON',
             '5': 'WAITING_FOR_INPUT',
             '6': 'UNKNOWN',
             '7': 'UNRECOGNIZED',
             '8': 'POWERED_OFF',
             '9': 'INCONSISTENT_STATE',
             '10': 'MIXED',
             '11': 'DESCRIPTOR_PENDING',
             '12': 'COPYING_CONTENTS',
             '13': 'DISK_CONTENTS_PENDING',
             '14': 'QUARANTINED',
             '15': 'QUARANTINE_EXPIRED',
             '16': 'REJECTED',
             '17': 'TRANSFER_TIMEOUT',
             '18': 'VAPP_UNDEPLOYED',
             '19': 'VAPP_PARTIALLY_DEPLOYED'}
        if str(self.status) in p.keys():
            self.status = p[str(self.status)]

    def powerOn(self, timeout: int = 300, check_time: int = 5):
        tree = self._action(self.href + '/power/action/powerOn', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def _powerOff(self, timeout: int = 300, check_time: int = 5):  # Hard, method for powering off without undeploying
        tree = self._action(self.href + '/power/action/powerOff', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def powerOff(self, timeout: int = 300, check_time: int = 5):  # Hard, with undeploy
        result = self.undeploy(timeout=timeout, checkTime=check_time, powerOffType='powerOff')
        if result is None:
            return None
        return self

    def renew(self, deploy_seconds: int = 86400, storage_seconds: int = 0):
        resp = requests.get(url=self.href + '/leaseSettingsSection', headers=self.headers)
        tree = treeify_xml(resp)

        tree.find('{*}DeploymentLeaseInSeconds').text = str(deploy_seconds)
        tree.find('{*}StorageLeaseInSeconds').text = str(storage_seconds)
        lease_section = etree.tostring(tree, encoding="utf-8", method="xml").decode('utf-8')
        requests.put(url=self.href + '/leaseSettingsSection', data=lease_section, headers=self.headers)

    def _shutdown(self, timeout: int = 300, check_time: int = 5):  # Soft, method for powering off without undeploying
        tree = self._action(self.href + '/power/action/shutdown', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def shutdown(self, timeout: int = 300, check_time: int = 5):  # Soft, with undeploy
        result = self.undeploy(timeout=timeout, checkTime=check_time, powerOffType='shutdown')
        print('Shutdown does not appear to work if all vms do not have vmware tools, use powerOff instead')
        if result is None:
            return None
        return self

    def _suspend(self, timeout: int = 300, check_time: int = 5):  # Method for suspending without undeploying
        tree = self.undeploy(timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def suspend(self, timeout: int = 300, check_time: int = 5):  # with undeploy
        result = self.undeploy(timeout=timeout, checkTime=check_time, powerOffType='suspend')
        if result is None:
            return None
        return self

    def reset(self, timeout: int = 300, check_time: int = 5):  # hard
        tree = self._action(self.href + '/power/action/reset', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def reboot(self, timeout: int = 300, check_time: int = 5):
        tree = self._action(self.href + '/power/action/reboot', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def unsuspend(self, timeout: int = 300, check_time: int = 5):
        tree = self._action(self.href + '/action/discardSuspendedState', timeout=timeout, checkTime=check_time)
        if tree is None:
            return None
        return self

    def genUndeployParams(self, powerOffType='default'):
        UndeployVAppParams = etree.Element('UndeployVAppParams')
        UndeployVAppParams.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        UndeployPowerAction = etree.SubElement(UndeployVAppParams, "UndeployPowerAction")
        UndeployPowerAction.text = powerOffType
        return etree.tostring(UndeployVAppParams).decode('utf-8')

    def undeploy(self, timeout: int = 300, checkTime: int = 5, powerOffType='default'):
        params = self.genUndeployParams(powerOffType=powerOffType)
        tree = self._action(self.href + '/action/undeploy', data=params, timeout=timeout, checkTime=checkTime)
        if tree is None:
            return None
        return self

    def _genSnapshotParams(self):
        CreateSnapshotParams = etree.Element('CreateSnapshotParams')
        CreateSnapshotParams.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        Description = etree.SubElement(CreateSnapshotParams, "Description")
        Description.text = "Snapshot"
        return etree.tostring(CreateSnapshotParams).decode('utf-8')

    def snapshot(self):
        params = self._genSnapshotParams()
        tree = self._action(self.href + '/action/createSnapshot', data=params)
        if tree is None:
            return None
        return self

    def revert(self):

        tree = self._action(self.href + '/action/revertToCurrentSnapshot')
        if tree is None:
            return None
        return self


class VAppTemplate(vObject):
    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('numberOfVMs', 'numberOfVMs')
        self.id = self.href.split('/api/vAppTemplate/')[1]

    def getVMTemplates(self):
        resp = requests.get(url=self.api + '/vAppTemplate/' + self.id, headers=self.headers)
        tree = treeify_xml(resp)
        children = tree.find('{*}Children')
        vms = children.findall('{*}Vm')
        return [VMTemplate(template, self.vcloud) for template in vms]

    def deploy2(self, vdc, name=None):
        params = self.vcloud.genInstantiateVAppTemplateParams(vAppHref=self.href, name=name)
        resp = requests.post(url=self.vcloud.api + '/vdc/' + vdc.id + '/action/instantiateVAppTemplate',
                             headers=self.headers, data=params)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)

        if 'Error' in tree.tag:
            print('Error:', tree.attrib['message'])
            return None
        return vApp(tree, self.vcloud)

    def deploy(self, vdc, name=None):
        params = self.vcloud.genInstantiateVAppTemplateParams(vAppHref=self.href, name=name)
        resp = requests.post(url=self.vcloud.api + "/vdc/" + vdc.id + "/action/instantiateVAppTemplate",
                             headers=self.headers, data=params)
        tree = treeify_xml(resp)

        if 'Error' in tree.tag:
            print('Error:', tree.attrib['message'])
            return None
        return vApp(tree, self.vcloud)


class orgVdc(vObject):
    findString = "{*}OrgVdcRecord"
    queryType = "orgVdc"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('orgName', 'org')
        self.addAttrib('numberOfVMs', 'numberOfVMs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')

        self.id = self.href.split('/api/vdc/')[1]


class Network(vObject):
    findString = "{*}OrgNetworkRecord"
    queryType = "orgNetwork"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('org', 'org')
        self.addAttrib('type', 'type')

        self.id = self.href.split('/api/network/')[1]

    def update(self):
        xml_content = self.getXML()
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        return Network(tree, self.vcloud)


class Task(vObject):
    findString = "{*}TaskRecord"
    queryType = "task"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

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


class VMTemplate(alive):
    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)
        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')

        self.id = self.href.split('/api/vAppTemplate/vm-')[1]


class VM(alive):
    findString = "{*}VMRecord"
    queryType = "vm"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('owner', 'owner')
        self.addAttrib('container', 'container')
        self.addAttrib('status', 'status')
        self.id = self.href.split('/api/vApp/vm-')[1]

        self.resolveStatus()

    def lastOpened(self):
        tasks = self.vcloud.getTasks('jobAcquireScreenTicket', object_href=self.href)
        tasks.sort(key=lambda x: x.startDate)
        if tasks is None or tasks == []:
            return None
        else:
            return (tasks[0].startDate)

    def checkGuestCustomization(self):
        string = self.getSection('GuestCustomizationSection').find('{*}Enabled').text
        if string == 'true':
            return True
        else:
            return False

    def setCustomProductSections(self, text: str, timeout: int = 300, check_time: int = 5):
        self.putCustomXML("/productSections", text, timeout=timeout, check_time=check_time)

    def getCustomProductSections(self) -> str:
        return requests.get(self.href + "/productSections", headers=self.vcloud.headers).text


class vApp(alive):
    findString = "{*}VAppRecord"
    queryType = "vApp"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('owner', 'owner')
        self.addAttrib('ownerName', 'ownerName')
        self.addAttrib('status', 'status')
        self.addAttrib('description', 'description')
        self.resolveStatus()

        self.id = self.href.split('/api/vApp/vapp-')[1]

    def capture(self, catalog, name=None, descriptionText=''):
        resp = self._action(catalog.href + '/action/captureVApp',
                            data=self._generateCaptureParams(name, descriptionText))
        if resp is None:
            return None
        else:
            return Task(resp, self.vcloud)

    def _generateCaptureParams(self, name, descriptionText):
        CaptureVAppParams = etree.Element('CaptureVAppParams')
        CaptureVAppParams.set("xmlns", "http://www.vmware.com/vcloud/v1.5")

        if name is None:
            CaptureVAppParams.set("name", self.name)
        else:
            CaptureVAppParams.set("name", name)

        Description = etree.SubElement(CaptureVAppParams, "Description")
        Description.text = descriptionText

        Source = etree.SubElement(CaptureVAppParams, "Source")
        Source.set('href', self.href)

        CustomizationSection = etree.SubElement(CaptureVAppParams, "CustomizationSection")
        Info = etree.SubElement(CustomizationSection, "{http://schemas.dmtf.org/ovf/envelope/1}Info")
        CustomizeOnInstantiate = etree.SubElement(CustomizationSection, "CustomizeOnInstantiate")
        CustomizeOnInstantiate.text = 'true'

        return etree.tostring(CaptureVAppParams).decode('utf-8')

    def recomposeVapp(self, text: str, timeout: int = 300, check_time: int = 5):
        self.postCustomXML("/action/recomposeVApp", text, timeout=timeout, check_time=check_time)

    def getVMs(self):
        resp = requests.get(url=self.href, headers=self.headers)
        tree = treeify_xml(resp)
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
    findString = "{*}UserRecord"
    queryType = "user"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')

        self.id = self.href.split('/api/admin/user/')[1]


class Role(vObject):
    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('fullName', 'fullName')
        self.addAttrib('roleNames', 'roleNames')
        self.addAttrib('isLdapUser', 'isLdapUser')
        self.id = self.href.split('/api/admin/role/')[1]


class Event(vObject):
    findString = "{*}EventRecord"
    queryType = "event"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

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
    findString = "{*}OrgRecord"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('numberOfCatalogs', 'numberOfCatalogs')
        self.addAttrib('numberOfVApps', 'numberOfVApps')
        self.addAttrib('numberOfVdcs', 'numberOfVdcs')

        self.id = self.href.split('/api/org/')[1]

    def _generateUserCreateParams(self, name, password, role):
        User = etree.Element('User')
        User.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        User.set("name", name)

        IsEnabled = etree.SubElement(User, "IsEnabled")
        IsEnabled.text = "true"
        Role = etree.SubElement(User, "Role")
        Role.set("href", role.href)
        Password = etree.SubElement(User, "Password")
        Password.text = password
        return etree.tostring(User).decode('utf-8')

    def createUser(self, name, password, role):
        newApi = self.href.replace('api', 'api/admin')
        params = self._generateUserCreateParams(name, password, role)
        resp = requests.post(url=newApi + '/users', headers=self.headers, data=params)
        tree = treeify_xml(resp)
        if tree is not None:
            return User(tree, self)
        else:
            return None

    def getUser(self, name, role=None):
        name = name.lower()
        resp = requests.get(url=self.api + f"/query?type=user&filter=name=={name}", headers=self.headers)
        result = self.vcloud.objectify_xml(resp, User)
        if len(result) == 0 and role is not None:
            return self.importUser(name, role)
        elif len(result) > 0:
            return result[0]
        else:
            return None

    def getUsers(self, name: str = "", role: Role = None) -> List[User]:
        if name != "": name = f"name=={name.lower()}"
        return self.vcloud.get_all(User, name)

    def getRole(self, name):
        resp = requests.get(url=self.api + f"/query?type=role&filter=name=={name}", headers=self.headers)
        tree = treeify_xml(resp)
        result = tree.find('{*}RoleRecord')
        if result is None:
            return None
        return Role(result, self)

    def importUser(self, name, role):
        params = self._generateUserParams(name, role)
        resp = requests.post(url=self.api + '/admin/org/' + self.id + '/users', headers=self.headers, data=params)
        tree = treeify_xml(resp)
        if 'Error' in tree.tag:
            print('Error:', tree.attrib['message'])
            return None
        return User(tree, self.vcloud)


class Catalog(vObject):
    findString = "{*}CatalogRecord"

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('orgName', 'org')
        self.id = self.href.split('/api/catalog/')[1]

    def createTemplate(self, vapp: vApp, name: str):
        if vapp.status != "POWERED_OFF":
            vapp.powerOff()
        self.postCustomXML("/action/captureVApp", f"""<?xml version="1.0" encoding="UTF-8"?>
<root:CaptureVAppParams xmlns:root="http://www.vmware.com/vcloud/v1.5" xmlns:ns1="http://schemas.dmtf.org/ovf/envelope/1" name="{name}">
   <root:Source href="{vapp.href}" />
   <root:CustomizationSection>
      <ns1:Info>CustomizeOnInstantiate Settings</ns1:Info>
      <root:CustomizeOnInstantiate>true</root:CustomizeOnInstantiate>
   </root:CustomizationSection>
</root:CaptureVAppParams>
""")

    def getTemplates(self, filter='*', vdc=None):
        if vdc is not None:
            resp = requests.get(
                url=self.api + '/vAppTemplates/query?pageSize=128&filter=(name==' + filter + ';vdc==' + vdc.href + ')',
                headers=self.headers)
        else:
            resp = requests.get(url=self.api + '/vAppTemplates/query?pageSize=128&filter=(name==' + filter + ')',
                                headers=self.headers)

        tree = treeify_xml(resp)
        results = tree.findall('{*}VAppTemplateRecord')
        return [VAppTemplate(template, self.vcloud) for template in results]


class Media(vObject):
    findString = '{*}MediaRecord'
    queryType = 'media'

    def __init__(self, dict, vcloud_obj):
        super().__init__(dict, vcloud_obj)

        self.addAttrib('catalog', 'catalogHref')
        self.addAttrib('owner', 'ownerHref')
        self.addAttrib('vdcName', 'vdcName')
        self.id = self.href.split('/media/')[1]

    def _generateCloneParams(self, name, deleteSource=False, description="Empty"):
        CloneMediaParams = etree.Element('CloneMediaParams')
        CloneMediaParams.set("xmlns", "http://www.vmware.com/vcloud/v1.5")
        CloneMediaParams.set("name", name)

        Description = etree.SubElement(CloneMediaParams, "Description")
        Description.text = description

        Source = etree.SubElement(CloneMediaParams, "Source")
        Source.set("href", self.href)
        Source.set("id", self.id)
        Source.set("type", "media")
        Source.set("name", self.name)

        IsSourceDelete = etree.SubElement(CloneMediaParams, "IsSourceDelete")
        if deleteSource:
            IsSourceDelete.text = "true"
        else:
            IsSourceDelete.text = "false"
        return etree.tostring(CloneMediaParams).decode('utf-8')

    def clone(self, name, vdc, deleteSource=False, description="Empty"):
        resp = self._action(f'{vdc.href}/action/cloneMedia',
                            data=self._generateCloneParams(name, deleteSource=deleteSource, description=description))
        print(resp.text)
        if resp is None:
            return None
        else:
            return Media(resp, self.vcloud)


class vcloud:

    def objectify_xml(self, response: requests.Response, obj_type) -> list:
        tree = treeify_xml(response)
        result = tree.findall(obj_type.findString)
        return [obj_type(data, self) for data in result]

    def __init__(self, config):
        print("Initializing vcloud object...")
        self.config = config
        self.user = config["main"]["user"]
        self.passwd = config["main"]["password"]
        self.host = config["main"]["host"]
        self.org = config["main"]["org"]

        self.api = f"https://{self.host}/api"
        self.session_url = f"{self.api}/sessions"

        self.headers = {"Accept": "application/*+xml;version=30.0"}
        self._set_auth_token()
        print("Finished initializing vcloud object...")

    def _set_auth_token(self):
        auth_str = '%s@%s:%s' % (self.user, self.org, self.passwd)
        auth = base64.b64encode(auth_str.encode()).decode('utf-8')
        self.headers['Authorization'] = f'Basic {auth}'
        resp = requests.post(url=self.session_url, headers=self.headers)
        del self.headers['Authorization']
        try:
            self.headers['x-vcloud-authorization'] = resp.headers['x-vcloud-authorization']
        except KeyError:
            print("Authentication Error! Are you sure your credentials are correct?")
            exit()

    def checkAuth(self, username, password):
        headers = {'Accept': 'application/*+xml;version=30.0'}

        auth_str = f'{username}@{self.org}:{password}'
        auth = base64.b64encode(auth_str.encode()).decode('utf-8')
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

    def getCatalog(self, name: str = "") -> Catalog:
        print("No bad this is deprecated use catalogS")
        resp = requests.get(url=self.api + f"/catalogs/query?filter=name=={name}", headers=self.headers)
        return self.objectify_xml(resp, Catalog)[0]

    def getCatalogs(self, name: str = "") -> List[Catalog]:
        if name != "": name = f"name=={name}"
        resp = requests.get(url=self.api + f"/catalogs/query?filter={name}", headers=self.headers)
        return self.objectify_xml(resp, Catalog)

    def getVdc(self, name: str) -> orgVdc:
        resp = requests.get(url=self.api + f"/query?type=orgVdc&filter=name=={name}", headers=self.headers)
        return self.objectify_xml(resp, orgVdc)[0]

    def getOrgNetworks(self, name: str = "") -> List[Network]:
        if name != "": name = f"name=={name}"
        return self.get_all(Network, name)

    def getOrg(self, name: str) -> Org:
        resp = requests.get(url=self.api + f"/admin/orgs/query?filter=name=={name}", headers=self.headers)
        return self.objectify_xml(resp, Org)[0]

    def getvApps(self, name: str = "") -> List[vApp]:
        if name != "": name = f"name=={name}"
        return self.get_all(vApp, name)

    def getMedia(self, filter: str = '*', vdc: str = None) -> List[Media]:
        if vdc is not None:
            filter = f"(name=={filter};vdc=={vdc.href})"
        else:
            filter = f"(name=={filter})"
        return self.get_all(Media, filter)

    def getVMs(self, name: str = "") -> List[VM]:
        if name != "": name = f";name=={name}"
        return self.get_all(VM, f"isVAppTemplate==false{name}")

    def getEvents(self) -> List[Event]:
        return self.get_all(Event)

    def getTasks(self, name: str = None, object_href: str = None, verbose: bool = False) -> List[Task]:
        args = []
        if name: args.append(f"name=={name}")
        if object_href: args.append(f"object=={object_href}")
        query_filter = ';'.join(args)
        return self.get_all(Task, query_filter, verbose)

    def get_all(self, query_type, query_filter: str = "", verbose: bool = False) -> list:
        list_of_objects = []
        for page in range(1, 9999):
            if verbose:
                print(f"Getting {query_type.queryType} page {page} :: {len(list_of_objects)}")
            response = requests.get(
                url=self.api + f"/query?type={query_type.queryType}&filter={query_filter}&pageSize=128&page={str(page)}",
                headers=self.headers)
            print(response.text)

            result = self.objectify_xml(response, query_type)
            if not result:
                break
            list_of_objects += result
        return list_of_objects

    def genInstantiateVAppTemplateParams(self, name=None, deploy=False, power_on=False, vAppHref=None):
        InstantiateVAppTemplateParams = etree.Element('InstantiateVAppTemplateParams')
        InstantiateVAppTemplateParams.set("xmlns", "http://www.vmware.com/vcloud/v1.5")

        if name is None:
            date = datetime.now().strftime("%Y-%m-%d-%H-%M-%S:%f")
            InstantiateVAppTemplateParams.set("name", date)
        else:
            InstantiateVAppTemplateParams.set("name", name)

        InstantiateVAppTemplateParams.set("deploy", str(deploy).lower())
        InstantiateVAppTemplateParams.set("powerOn", str(power_on).lower())

        InstantiationParams = etree.SubElement(InstantiateVAppTemplateParams, "InstantiationParams")

        if vAppHref is not None:
            Source = etree.SubElement(InstantiateVAppTemplateParams, "Source")
            Source.set("href", vAppHref)

        return etree.tostring(InstantiateVAppTemplateParams).decode('utf-8')
