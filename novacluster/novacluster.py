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


# the default logger; doesn't do anything
class NoLogger(object):
    def log(self, string):
        pass


def _get_user_data(file_path, format_dict):
    ''' Read file and format with format_dict'''
    with open(file_path) as script:
        script = script.read() % format_dict
    return script


def _generate_id():
    """Generate an id for a new cluster."""
    rand_base = "0000000%s" % random.randrange(sys.maxint)
    date = datetime.datetime.now()
    return "%s-%s" % (rand_base[-8:], date.strftime("%m-%d-%y"))


def _get_cores(client, flavor):
    """Use the novaclient to get the cores for a given flavor."""
    return client.flavors.get(flavor).vcpus


def _get_package_script(script_name):
    """Get the path to a script packaged with the module."""
    base_dir = os.path.dirname(__file__)
    return base_dir + "/scripts/" + script_name


def _get_cluster_theme_scripts(theme):
    """Return a tuple of the base64encoded head node and compute node
    scripts for a given cluster theme. Returns None if a cluster has
    no such script."""
    head_script = theme.get("head_script")
    compute_script = theme.get("compute_script")
    head_script = open(head_script).read() if head_script else "None"
    compute_script = open(compute_script).read() if compute_script else "None"
    return base64.b64encode(head_script), base64.b64encode(compute_script)


def dict_subset(d1, d2):
    """Return true if d2 is contained within d1."""
    if type(d1) is not dict or type(d2) is not dict:
        return False
    res = []
    for key, val in d2.items():
        if key in d1.keys():
            if type(val) is dict:
                res.append(dict_subset(d1[key], val))
            elif val != d1[key]:
                return False
        else:
            return False
    return all(res)


def _find_image(client, spec):
    """Return the first image that matches the restrictions
    specified by the dictionary."""
    images = client.images.list()
    for image in images:
        if dict_subset(image.__dict__, spec):
            return image
    raise RuntimeError("No image matches this specification, "
                       "make sure the theme is set up correctly.")


def _run_ssh_on_string(command, string):
    temp = tempfile.NamedTemporaryFile(delete=False)
    temp.write(string)
    temp.close()

    process = Popen(command % temp.name, stdout=PIPE, shell=True)
    exit_code = os.waitpid(process.pid, 0)
    output = process.communicate()[0]

    os.unlink(temp.name)

    return output


def _generate_keypair(password=None):
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

    public_key = _run_ssh_on_string(SSH_KEYGEN_COMMAND + " -f %s -i -m PKCS8",
                                    mem_pub.getvalue())[:-1]
    return {"public": public_key, "private": private_key}


def launch_headnode(cloud, client, clientinfo, cluster_id, n_compute_nodes,
                    cluster_theme, os_key_name, user_script, ssh_keys, cores):
    # make headnode user data
    headnode_user_data = _get_user_data(
        _get_package_script("torque_server.py"),
        {"username": clientinfo["username"],
         "password": clientinfo["password"],
         "auth_url": clientinfo["auth_url"],
         "auth_token": client.client.auth_token,
         "cluster_id": cluster_id, "nodes": n_compute_nodes,
         "compute_url": client.client.management_url,
         "headnode_script": HEADNODE_SCRIPT,
         "pdc": "True" if cloud == "pdc" else "False",
         "cores": cores,
         "user_script": user_script,
         "public_key": ssh_keys["public"],
         "private_key": ssh_keys["private"]})

    return client.servers.create(
        "torque-headnode-{0}".format(cluster_id),
        _find_image(client, cluster_theme["head"]),
        client.flavors.get(3),  # should be medium
        userdata=headnode_user_data,
        key_name=os_key_name,
        security_groups=["default"])


def launch_compute_nodes(cloud, client, clientinfo, cluster_id,
                         n_compute_nodes, cluster_theme, os_key_name,
                         user_script, ssh_keys, node_flavor):
    # make compute node user data
    compute_node_user_data = _get_user_data(
        _get_package_script("torque-node.sh"),
        {"username": clientinfo["username"],
         "node_script": COMPUTE_NODE_SCRIPT,
         "pdc": "true" if cloud == "pdc" else "false",
         "cluster_id": cluster_id,
         "user_script": user_script,
         "public_key": ssh_keys["public"],
         "private_key": ssh_keys["private"]})

    # launch the compute nodes
    return client.servers.create(
        "torque-node-{0}".format(cluster_id),
        _find_image(client, cluster_theme["compute"]),
        client.flavors.get(node_flavor),
        userdata=compute_node_user_data,
        min_count=n_compute_nodes,
        max_count=n_compute_nodes,
        key_name=os_key_name,
        security_groups=["default"])


def _make_novaclient(clientinfo):
    """Create an OpenStack nova client object."""
    return nc.Client(VERSION,
                     clientinfo["username"],
                     clientinfo["password"],
                     clientinfo["tenant_name"],
                     clientinfo["auth_url"],
                     service_type="compute")


def cluster_launch(cloud, clientinfo, n_compute_nodes, cluster_theme,
                   node_flavor, os_key_name=None, cluster_id=None,
                   logger=None):
    """Launch a new cluster."""

    if logger is None:
        logger = NoLogger()
    logger.log("connecting to OpenStack API . . .")

    # make a new novaclient
    client = _make_novaclient(clientinfo)

    # if we weren't passed an id, generate one
    if cluster_id is None:
        cluster_id = _generate_id()

    if node_flavor is None:
        node_flavor = 3  # use medium as a default

    cores = _get_cores(client, node_flavor)

    if os_key_name is None:
        try:
            os_key_name = client.keypairs.list()[0].name
        except IndexError:
            raise RuntimeError("No keypairs found; ensure"
                               "that you have uploaded a keypair"
                               "to the OpenStack API.")

    logger.log("Launching new cluster with id {0} and"
               " {1} compute nodes.".format(cluster_id, n_compute_nodes))

    # get the user's scripts for embedding
    head_script, compute_script = _get_cluster_theme_scripts(cluster_theme)

    # generate keypair for sullivan
    ssh_keys = _generate_keypair()

    # launch the headnode
    logger.log("Launching headnode . . .")
    try:
        headnode = launch_headnode(cloud, client, clientinfo,
                                   cluster_id, n_compute_nodes,
                                   cluster_theme, os_key_name,
                                   head_script, ssh_keys, cores)
    except:
        raise RuntimeError("Failed to create headnode, bailing . . .")

    logger.log("Launching compute nodes . . .")
    try:
        launch_compute_nodes(cloud, client, clientinfo, cluster_id,
                             n_compute_nodes, cluster_theme,
                             os_key_name, compute_script, ssh_keys,
                             node_flavor)
    except:
        # compute nodes failed, kill the headnode
        client.servers.delete(headnode)
        raise RuntimeError("Failed to create compute nodes,"
                           "killing headnode and bailing . . .")

    # it worked!
    logger.log("Cluster launched successfully.")
    return headnode


def list_clusters(clientinfo, logger=None):
    """Return a list of ids of the user's clusters."""

    if logger is None:
        logger = NoLogger()  # a logger that simpley doesn't do anything

    logger.log("connecting to OpenStack API . . .")

    # make a client
    client = _make_novaclient(clientinfo)

    logger.log("Retrieving cluster info . . .")

    # get the id of each cluster
    names = [server.name.replace("torque-headnode-", "")
             for server in client.servers.list()
             if "torque-headnode-" in server.name]

    # TODO: include some information about each cluster, e.g. # compute nodes

    return names


def delete_cluster(clientinfo, cluster_id, logger=None):
    """Delete the cluster with a given id."""

    if logger is None:
        logger = NoLogger()  # a logger that simpley doesn't do anything

    logger.log("connecting to OpenStack API . . .")

    # make a client
    client = _make_novaclient(clientinfo)

    logger.log("Deleting cluster . . .")

    # figure out which nodes to delete
    nodes = [server for server in client.servers.list()
             if cluster_id in server.name]

    # send delete requests
    for node in nodes:
        client.servers.delete(node)

    logger.log("Cluster deleted successfully.")

    return
