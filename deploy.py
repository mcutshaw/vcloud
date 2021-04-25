import time
from json import load
from multiprocessing import Pool

from vcloud import vcloud


def deployToUser(tup):
    user = tup[0]
    template = tup[1]
    vdc = tup[2]
    if user is None:
        return
    vapp = template.deploy(vdc, name=template.name + '_' + user.name)
    if vapp is None:
        return
    endvapp = vapp.changeOwner(user, timeout=300, check_time=5)
    if endvapp is not None:
        print(user.name + '_' + template.name, 'deployed successfully deployed to', user.name)


if __name__ == '__main__':
    start_time = time.time()
    with open("vcloud.json", "r") as file:
        config = load(file)
    filters = config['Extra']['Filters'].split(',')
    vcloud = vcloud(config)
    catalog = vcloud.getCatalog(config['Extra']['Catalog'])
    vdc = vcloud.getVdc(config['Extra']['Vdc'])
    org = vcloud.getOrg(config['Main']['Org'])
    role = org.getRole(config['Deploy']['Role'])

    p = Pool(12)

    templates = catalog.getTemplates(filter='DefSec_ESXi')
    template = templates[0]

    with open('users.txt', 'r') as f:
        users = f.read().split('\n')

    l = []
    for user in users:
        user = org.getUser(user, role=role)
        l.append((user, template, vdc))

    p.map(deployToUser, l)
    print("Deploy took", (time.time() - start_time), "seconds.")
