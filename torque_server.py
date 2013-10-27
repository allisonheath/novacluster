#!/usr/bin/python

import getpass
import json
import os
import sys
import time
from novaclient import client as nc

VERION = "1.1"

username = "%(username)s"
password = "%(password)s"
auth_url = "%(auth_url)s"

client = nc.Client(VERSION,username,password,username,auth_url,service_type="compute")

cluster_id = "%(cluster_id)s"

if %(pdc)s and getpass.getuser() != username:
    sys.exit(1)

# wait for gluster to come up
while not os.path.exists("/glusterfs/"):
    time.wait(1)

ips = ""

servers = [i for i in nc.servers.list()
           if i.name == "torque-node-" + cluster_id]

for i in servers:
    try:
        ips = " ".join([ips, i.addresses["private"][0]["addr"]])
    except KeyError:
        pass

ips = '"' + ips + '"'


os.system(" ".join(["sudo", "%(headnode_script)s", cluster_id, ips, "%(cores)s"]))

os.system("echo ran /tmp/worked")
