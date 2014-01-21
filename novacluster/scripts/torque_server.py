#!/usr/bin/python

import getpass
import json
import os
import sys
import time
import urllib2
import base64

VERION = "1.1"

username = "%(username)s"
auth_token = "%(auth_token)s"
compute_url = "%(compute_url)s"
cluster_id = "%(cluster_id)s"

if False and getpass.getuser() != username:
    sys.exit(1)

# wait for torque dir
while not os.path.exists("%(headnode_script)s"):
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

# do ssh key stuff
if not %(pdc)s:
    os.system("echo %(public_key)s >> /home/ubuntu/.ssh/authorized_keys")
    os.system("""echo "%(private_key)s" >> /home/ubuntu/.ssh/id_dsa""")
    os.system("chown ubuntu:ubuntu /home/ubuntu/.ssh/id_dsa")
    os.system("chmod 600 /home/ubuntu/.ssh/id_dsa")

# run headnode script
os.system(" ".join(["sudo", "%(headnode_script)s",
                    cluster_id, ips, "%(cores)s", "%(username)s"]))

os.system("echo headnode script > /tmp/worked")

# run user script
# this is disgusting, but for some reason it wouldn't work
# using python's base64 decode module
os.popen("""
bash -c '
user_script=`echo "%(user_script)s" | base64 --decode`
if [[ $user_script != None ]]
then
    echo "$user_script" > /tmp/user_script
    sudo chmod a+x /tmp/user_script
    sudo /tmp/user_script
fi'
""")

os.system("echo user script >> /tmp/worked")
