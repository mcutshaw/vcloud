from vcloud import vcloud
import configparser
import time

config = configparser.ConfigParser()
config.read('vcloud.conf')
filters = config['Extra']['Filters'].split(',')
vcloud = vcloud(config)
catalog = vcloud.getCatalog(config['Extra']['Catalog'])
vdc = vcloud.getVdc(config['Extra']['Vdc'])
org = vcloud.getOrg(config['Main']['Org'])
role = org.getRole(config['Deploy']['Role'])

templates = catalog.getTemplates(filter='Blank')
with open('users.txt','r') as f:
    users = f.read().split('\n')
for struser in users:
    for template in templates:
        user = org.getUser(struser, role=role)
        if user is None:
            continue
        vapp = template.deploy(vdc,name=user.name+'_'+template.name)
        if vapp is None:
            continue
        endvapp = vapp.changeOwner(user, timeout=300, checkTime=5)
        if endvapp is not None:
            print(user.name+'_'+template.name, 'deployed successfully deployed to', user.name)

