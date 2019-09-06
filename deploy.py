from vcloud import vcloud
import configparser
import time
from multiprocessing import Pool


def deployToUser(tup):
    user = tup[0]
    template = tup[1]
    vdc = tup[2]
    if user is None:
        return
    vapp = template.deploy(vdc,name=user.name+'_'+template.name)
    if vapp is None:
        return
    endvapp = vapp.changeOwner(user, timeout=300, checkTime=5)
    if endvapp is not None:
        print(user.name+'_'+template.name, 'deployed successfully deployed to', user.name)

if __name__ == '__main__':
    start_time = time.time()
    config = configparser.ConfigParser()
    config.read('vcloud.conf')
    filters = config['Extra']['Filters'].split(',')
    vcloud = vcloud(config)
    catalog = vcloud.getCatalog(config['Extra']['Catalog'])
    vdc = vcloud.getVdc(config['Extra']['Vdc'])
    org = vcloud.getOrg(config['Main']['Org'])
    role = org.getRole(config['Deploy']['Role'])

    p = Pool(3)


    templates = catalog.getTemplates(filter='Blank')
    template = templates[0]

    with open('users.txt','r') as f:
        users = f.read().split('\n')
    
    l = []
    for user in users:
        user = org.getUser(user, role=role)
        l.append((user, template, vdc))

    p.map(deployToUser, l)
    print("Deploy took", (time.time() - start_time), "seconds.")
    

