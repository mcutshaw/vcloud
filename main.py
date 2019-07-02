from vcloud import vcloud
import configparser

config = configparser.ConfigParser()
config.read('renew.conf')
vcloud = vcloud(config)
defsec = vcloud.getCatalog('DefSec')
templates = defsec.getTemplates(filter='*Base*')
for template in templates:
    template.renew()
