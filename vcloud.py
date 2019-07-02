#!/usr/bin/python3
import base64
from requests.auth import HTTPBasicAuth
from lxml import etree, objectify
import configparser
import requests

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
        #print(xml_content.decode('utf-8'))
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        result = tree.find('{*}CatalogRecord')
        return Catalog(result.attrib, self)

class VAppTemplate:
    def __init__(self, dict, vcloud):
        self.dict = dict
        self.addAttrib('name', 'name')
        self.addAttrib('org', 'org')
        self.addAttrib('vdc', 'vdc')
        self.addAttrib('numberOfVMs', 'VMNum')
        self.addAttrib('href', 'href')
        self.id = self.href.split('/api/vAppTemplate/')[1]

        self.headers = vcloud.headers
        self.api = vcloud.api

    def addAttrib(self, key, name):
        if key in self.dict:
            setattr(self, name, self.dict[key])
        else:
            setattr(self, name, None)

    def renew(self, leaseSecs=7776000):
        
        resp = requests.get(url=self.api+'/vAppTemplate/'+self.id+'/leaseSettingsSection', headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)

        tree.find('{*}StorageLeaseInSeconds').text = str(leaseSecs)
        leaseSection = etree.tostring(tree, encoding="utf-8", method="xml").decode('utf-8')

        resp = requests.put(url=self.api+'/vAppTemplate/'+self.id+'/leaseSettingsSection', data=leaseSection, headers=self.headers)
        

class Catalog:
    def __init__(self, dict, vcloud):
        self.vcloud = vcloud
        self.dict = dict    
        self.addAttrib('name', 'name')
        self.addAttrib('orgName', 'org')
        self.addAttrib('href', 'href')

        self.headers = self.vcloud.headers
        self.api = self.vcloud.api

    def addAttrib(self, key, name):
        if key in self.dict:
            setattr(self, name, self.dict[key])
        else:
            setattr(self, name, None)
        
    def getTemplates(self, filter='*'):
        resp = requests.get(url=self.api+'/vAppTemplates/query?pageSize=128&filter=(catalogName=='+self.name+';name=='+ filter+')',headers=self.headers)
        xml_content = resp.text.encode('utf-8')
        parser = etree.XMLParser(ns_clean=True, recover=True)
        tree = etree.fromstring(bytes(xml_content), parser=parser)
        results = tree.findall('{*}VAppTemplateRecord')
        return [VAppTemplate(template.attrib, self.vcloud) for template in results]


