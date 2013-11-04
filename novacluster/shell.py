import argparse
import novacluster as nc
import os
import yaml

BUILTIN_THEMES = os.path.dirname(__file__) + "/builtin-themes.yaml"

# map from auth_urls to cloud names
# we use this to determine which cloud the user is targeting
# this is necessary because different clouds have different default
# image IDs.
CLOUD_MAP = {"http://cloud-controller:5000/v2.0/": "pdc",
             "https://api.opensciencedatacloud.org:5000/sullivan/v2.0/": "sullivan",
             "http://127.0.0.2:5100/v2.0": "pdc"}


def _get_cluster_theme(name):
    theme = yaml.load(open(BUILTIN_THEMES)).get(name)
    if theme is None:
        raise KeyError("Theme name not recognized")
    return theme


def get_from_env(key):
    """Attempt to get a key from the environment, throwing an error if
    the key does not exist"""
    try:
        return os.environ[key]
    except:
        raise KeyError("Environment not configured properly.")

# ye olde argparse incantations
parser = argparse.ArgumentParser(description="wrapper around novaclient for"
                                 "launching clusters of OSDC systems.")

subparsers = parser.add_subparsers(help='subcommand should be one of [launch, delete]',
                                   dest="subcommand")

launch_parser = subparsers.add_parser("launch", help="launch a new cluster")
launch_parser.add_argument("number", type=int, help="number of compute nodes")
launch_parser.add_argument("--key", type=str,
                           help="location of the ssh key"
                                "to use for this cluster")
launch_parser.add_argument("--flavor", type=int,
                           help="the flavor ID to use for"
                                "the compute nodes")


def main():
    args = parser.parse_args()
    # print args
    clientinfo = {
        "username": get_from_env("OS_USERNAME"),
        "password": get_from_env("OS_PASSWORD"),
        "auth_url": get_from_env("OS_AUTH_URL")
    }

    # determine cloud and cluster theme
    cloud = CLOUD_MAP.get(clientinfo["auth_url"])
    if cloud is None:
        raise RuntimeError("Your environments Openstack Auth URL"
                           "is not known to correspond to any OSDC"
                           "system. Please make sure your environment"
                           "is configured correctly.")
    # for now just launch the cloud's default theme
    cluster_theme = _get_cluster_theme(cloud)

    # for now just try to launch a cluster
    if args.subcommand == "launch":
        nc.cluster_launch(clientinfo, args.number, cluster_theme,
                          args.flavor, key_name=args.key)
