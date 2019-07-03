from vcloud import vcloud
import configparser

config = configparser.ConfigParser()
config.read('renew.conf')
filters = config['Renew']['Filters'].split(',')
vcloud = vcloud(config)
defsec = vcloud.getCatalog('DefSec')
for filt in filters:
    templates = defsec.getTemplates(filter=filt)
    for template in templates:
        template.renew()
        print(template.name)