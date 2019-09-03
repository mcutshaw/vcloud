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

vapps = vcloud.getvApps(config['MassRemove']['Filters'])
for vapp in vapps:
    vapp.delete()
 
