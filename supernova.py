from novaclient import client as nc
import argparse
import base64
import random
import sys
import datetime
from os import environ as env


FLAVORS = {"bcbio-nextgen":{"node-image":""}}
DEFAULT_HEADNODE_IMAGE = "43ad2a59-83bb-45c9-87e7-910f924f1ca7"
DEFAULT_COMPUTE_IMAGE = "a0b3f4fd-6b26-42f0-ba9c-aa51ba365fe1"
VERSION = "1.1"
HEADNODE_SCRIPT = "/cloudconf/torque/tukey_headnode.sh"
COMPUTE_NODE_SCRIPT = "/cloudconf/torque/tukey_node.sh"


def get_images(cluster_flavor):
    """Lookup the image ids we should be using to launch this cluster flavor"""
    print cluster_flavor
    if cluster_flavor is None:
        return DEFAULT_COMPUTE_IMAGE, DEFAULT_HEADNODE_IMAGE
    elif cluster_flavor not in FLAVORS.keys():
        raise KeyError("No such cluster flavor!")
    else:
        return FLAVORS[cluster_flavor]["compute_image"], FLAVORS[cluster_flavor]["head_image"]


def get_from_env(key):
    """Attempt to get a key from the environment, throwing an error if
    the key does not exist"""
    try:
        return env[key]
    except:
        raise KeyError("Environment not configured properly.")


def get_user_data(file_path, format_dict):
    ''' Read file and format with the dict then b64 encode'''
    with open(file_path) as script:
        script = script.read() % format_dict
    return script


def get_cores(client,flavor):
    """Use the novaclient to get the cores for a given flavor."""
    return client.flavors.get(flavor).vcpus


def launch_instances(client, clientinfo, cluster_id, n_compute_nodes, cores,
                     node_image_id, headnode_image_id, node_flavor, key_name):
    """Launch tiny headnode and compute nodes for a new cluster"""

    # make headnode user data
    headnode_user_data = get_user_data("/glusterfs/users/jporter/supernova/torque_server.py",
                                        {"username": clientinfo["username"],
                                         "password": clientinfo["password"],
                                         "auth_url": clientinfo["auth_url"],
                                         "auth_token": client.client.auth_token,
                                         "cluster_id": cluster_id, "nodes": n_compute_nodes,
                                         "compute_url": client.client.management_url,
                                         "headnode_script": HEADNODE_SCRIPT,
                                         "pdc": "False", # presumably this can be determined from the auth url?
                                         "cores": cores})


    # launch the headnode
    try:
        headnode = client.servers.create("torque-headnode-{0}".format(cluster_id),
                                         client.images.get(headnode_image_id),
                                         client.flavors.get(1), # should be tiny
                                         userdata=headnode_user_data,
                                         key_name=key_name,
                                         security_groups=["default"])
    except:
        raise RuntimeError("Failed to create headnode, bailing . . .")

    # make compute node user data
    compute_node_user_data = get_user_data("/glusterfs/users/jporter/supernova/torque-node.sh",
                                           {"username": clientinfo["username"],
                                            "node_script": COMPUTE_NODE_SCRIPT,
                                            "pdc":"false",
                                            "cluster_id": cluster_id})

    # launch the compute nodes
    # try:
    client.servers.create("torque-node-{0}".format(cluster_id),
                          client.images.get(node_image_id),
                          client.flavors.get(node_flavor),
                          userdata=compute_node_user_data,
                          min_count=n_compute_nodes,
                          max_count=n_compute_nodes,
                          key_name=key_name,
                          security_groups=["default"])
    # except:
    #     # compute nodes failed, kill the headnode
    #     client.servers.delete(headnode)
    #     raise RuntimeError("Failed to create comupte nodes, bailing . . .")

    # it worked!
    return




def cluster_launch(client, clientinfo, n_compute_nodes, cluster_flavor, node_flavor):
    """Launch a new cluster."""

    node_image_id, headnode_image_id = get_images(cluster_flavor)

    # generate cluster_id
    rand_base = "0000000%s" % random.randrange(sys.maxint)
    date = datetime.datetime.now()
    cluster_id = "%s-%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))

    cores = get_cores(client,node_flavor)

    key_name = "bcbio" #FIXME

    # launch the instances
    launch_instances(client, clientinfo, cluster_id, n_compute_nodes, cores,
                     node_image_id, headnode_image_id, node_flavor,key_name)


if __name__ == "__main__":
    # make a new novaclient
    clientinfo = {
        "username": get_from_env("OS_USERNAME"),
        "password": get_from_env("OS_PASSWORD"),
        "auth_url": get_from_env("OS_AUTH_URL")
    }
    client = nc.Client(VERSION,
                       clientinfo["username"],
                       clientinfo["password"],
                       clientinfo["username"],
                       clientinfo["auth_url"],
                       service_type="compute")

    # for now just try to launch a cluster
    cluster_launch(client, clientinfo, 3, None, 3)
