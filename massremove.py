import configparser
import time

from vcloud import vcloud

start_time = time.time()

config = configparser.ConfigParser()
config.read('vcloud.conf')
filters = config['Extra']['Filters'].split(',')
vcloud = vcloud(config)
catalog = vcloud.getCatalog(config['Extra']['Catalog'])
vdc = vcloud.getVdc(config['Extra']['Vdc'])
org = vcloud.getOrg(config['Main']['Org'])
role = org.getRole(config['Deploy']['Role'])

vapps = []
for filter in config['MassRemove']['Filters'].split(','):
    vapps += vcloud.getvApps(filter)
print(len(vapps))
for vapp in vapps:
    print(vapp.name)
    vapp.delete()

print("Remove took", (time.time() - start_time), "seconds.")
