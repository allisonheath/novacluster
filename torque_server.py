#!/usr/bin/python

import getpass
import json
import os
import sys
import time
import urllib2

VERION = "1.1"

username = "%(username)s"
auth_token = "%(auth_token)s"
compute_url = "%(compute_url)s"
cluster_id = "%(cluster_id)s"

if False and getpass.getuser() != username:
    sys.exit(1)

# wait for torque dir
while not os.path.exists("/cloudconf/torque/setup_scripts"):
    time.wait(1)

req = urllib2.Request(compute_url + "/servers/detail",headers={"x-auth-project-d": username, "x-auth-token": auth_token})
resp = urllib2.urlopen(req)

servers = [i for i in json.loads(resp.read())["servers"]
           if i["name"] == "torque-node-" + cluster_id]

ips = ""

for i in servers:
    try:
        ips = " ".join([ips, i["addresses"]["private"][0]["addr"]])
    except KeyError:
        pass

ips = '"' + ips + '"'


os.system(" ".join(["sudo", "%(headnode_script)s", cluster_id, ips, "%(cores)s"]))

os.system("echo ran /tmp/worked")
