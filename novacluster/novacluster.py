from novaclient import client as nc
import random
import sys
import datetime
import os
import tempfile
import base64
from M2Crypto import DSA, BIO
from subprocess import Popen, PIPE

# Openstack nova client version
VERSION = "1.1"
# locations of scripts to be run during cluster startup
HEADNODE_SCRIPT = "/cloudconf/torque/tukey_headnode.sh"
COMPUTE_NODE_SCRIPT = "/cloudconf/torque/tukey_node.sh"
SSH_KEYGEN_COMMAND = "ssh-keygen"


def get_user_data(file_path, format_dict):
    ''' Read file and format with format_dict'''
    with open(file_path) as script:
        script = script.read() % format_dict
    return script


def get_cores(client, flavor):
    """Use the novaclient to get the cores for a given flavor."""
    return client.flavors.get(flavor).vcpus


def _get_package_script(script_name):
    """Get the path to a script packaged with the module."""
    base_dir = os.path.dirname(__file__)
    return base_dir + "/scripts/" + script_name


def _get_cluster_theme_scripts(theme):
    """Return a tuple of the head node and compute node
    scripts for a given cluster theme. Returns None if
    a cluster has no such script."""
    head_script = theme.get("head_script")
    compute_script = theme.get("compute_script")
    head_script = open(head_script).read() if head_script else "None"
    compute_script = open(compute_script).read() if compute_script else "None"
    return base64.b64encode(head_script), base64.b64encode(compute_script)


def run_ssh_on_string(command, string):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(string)
    temp.close()

    process = Popen(command % temp.name, stdout=PIPE, shell=True)
    exit_code = os.waitpid(process.pid, 0)
    output = process.communicate()[0]

    os.unlink(temp.name)

    return output


def generate_keypair(password=None):
    dsa = DSA.gen_params(1024, os.urandom)

    mem_pub = BIO.MemoryBuffer()
    mem_private = BIO.MemoryBuffer()

    dsa.gen_key()
    if password is None:
        dsa.save_key_bio(mem_private, cipher=None)
    else:
        dsa.save_key_bio(mem_private, callback=lambda _: password)

    private_key = mem_private.getvalue()

    dsa.save_pub_key_bio(mem_pub)

    public_key = run_ssh_on_string(SSH_KEYGEN_COMMAND + " -f %s -i -m PKCS8",
                                   mem_pub.getvalue())[:-1]
    return public_key, private_key


def launch_instances(client, clientinfo, cluster_id, n_compute_nodes, cores,
                     cluster_theme, node_flavor, key_name):
    """Launch tiny headnode and compute nodes for a new cluster"""

    head_user_script, compute_user_script = _get_cluster_theme_scripts(cluster_theme)
    public_key, private_key = generate_keypair()

    # make headnode user data
    headnode_user_data = get_user_data(_get_package_script("torque_server.py"),
                                       {"username": clientinfo["username"],
                                        "password": clientinfo["password"],
                                        "auth_url": clientinfo["auth_url"],
                                        "auth_token": client.client.auth_token,
                                        "cluster_id": cluster_id, "nodes": n_compute_nodes,
                                        "compute_url": client.client.management_url,
                                        "headnode_script": HEADNODE_SCRIPT,
                                        "pdc": "False",  # presumably this can be determined from the auth url?
                                        "cores": cores,
                                        "user_script": head_user_script,
                                        "public_key": public_key,
                                        "private_key": private_key})

    # launch the headnode
    try:
        headnode = client.servers.create("torque-headnode-{0}".format(cluster_id),
                                         client.images.get(cluster_theme["head_image"]),
                                         client.flavors.get(3),  # should be medium
                                         userdata=headnode_user_data,
                                         key_name=key_name,
                                         security_groups=["default"])
    except:
        raise RuntimeError("Failed to create headnode, bailing . . .")

    # make compute node user data
    compute_node_user_data = get_user_data(_get_package_script("torque-node.sh"),
                                           {"username": clientinfo["username"],
                                            "node_script": COMPUTE_NODE_SCRIPT,
                                            "pdc": "false",
                                            "cluster_id": cluster_id,
                                            "user_script": compute_user_script,
                                            "public_key": public_key,
                                            "private_key": private_key})


    # launch the compute nodes
    try:
        client.servers.create("torque-node-{0}".format(cluster_id),
                              client.images.get(cluster_theme["head_image"]),
                              client.flavors.get(node_flavor),
                              userdata=compute_node_user_data,
                              min_count=n_compute_nodes,
                              max_count=n_compute_nodes,
                              key_name=key_name,
                              security_groups=["default"])
    # compute nodes failed, kill the headnode
    except:
        client.servers.delete(headnode)
        raise RuntimeError("Failed to create comupte nodes, bailing . . .")

    # it worked!
    return


def cluster_launch(clientinfo, n_compute_nodes, cluster_theme,
                   node_flavor, key_name=None):
    """Launch a new cluster."""

    # make a new novaclient
    client = nc.Client(VERSION,
                       clientinfo["username"],
                       clientinfo["password"],
                       clientinfo["tenant_name"],
                       clientinfo["auth_url"],
                       service_type="compute")

    # generate cluster_id
    rand_base = "0000000%s" % random.randrange(sys.maxint)
    date = datetime.datetime.now()
    cluster_id = "%s-%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))

    cores = get_cores(client, node_flavor)

    # launch the instances
    launch_instances(client, clientinfo, cluster_id, n_compute_nodes, cores,
                     cluster_theme, node_flavor, key_name)
