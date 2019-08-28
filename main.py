from vcloud import vcloud
import configparser
import time

config = configparser.ConfigParser()
config.read('renew.conf')
filters = config['Renew']['Filters'].split(',')
vcloud = vcloud(config)
defsec = vcloud.getCatalog(config['Renew']['Catalog'])
vdc = vcloud.getVdc(config['Renew']['Vdc'])

for filt in filters:
    templates = defsec.getTemplates(filter=filt)
    for template in templates:
            template.deploy(vdc, name='testingdeploy_1'+vdc.id)
