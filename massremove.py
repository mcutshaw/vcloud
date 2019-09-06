from vcloud import vcloud
import configparser
import time

start_time = time.time()

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
 
print("Remove took", (time.time() - start_time), "seconds.")