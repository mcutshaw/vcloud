from vcloud import vcloud
import configparser
import time
from datetime import datetime

start_time = time.time()

config = configparser.ConfigParser()
config.read('vcloud.conf')
filters = config['Extra']['Filters']
vcloud = vcloud(config)
catalog = vcloud.getCatalog(config['Extra']['Catalog'])
vdc = vcloud.getVdc(config['Extra']['Vdc'])
org = vcloud.getOrg(config['Main']['Org'])
role = org.getRole(config['Deploy']['Role'])

l = []
tasks = vcloud.getTasks()
for task in tasks:
    if task.name == 'jobAcquireScreenTicket':
        if task.startDate.weekday() == 1 and task.startDate.hour > 17 and task.startDate.hour < 20:
            if task.ownerName not in l:
                l.append(task.ownerName)

for item in l:
    print(item)
print("Deploy took", (time.time() - start_time), "seconds.")