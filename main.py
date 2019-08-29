from vcloud import vcloud
import configparser
import time

config = configparser.ConfigParser()
config.read('renew.conf')
filters = config['Renew']['Filters'].split(',')
vcloud = vcloud(config)
defsec = vcloud.getCatalog(config['Renew']['Catalog'])
vdc = vcloud.getVdc(config['Renew']['Vdc'])
org = vcloud.getOrg(config['Main']['Org'])
role = org.getRole(config['Deploy']['Role'])


user = org.importUser("tgsereda",role)
print(user)
print(user.name)
print(user.fullName)

