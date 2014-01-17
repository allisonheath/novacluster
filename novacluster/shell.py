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


def _get_cluster_theme(cloud, theme_name):
    # base loader is necessary so that it doesn't try to convert things
    # to Python types; which is problematic when comparing to the results
    # returned from the Nova API
    themes = yaml.load(open(BUILTIN_THEMES), Loader=yaml.BaseLoader)
    user_themes_filename = os.path.expanduser("~/.novacluster_themes")
    if os.path.exists(user_themes_filename):
        user_themes = yaml.load(open(user_themes_filename))
    theme = themes[cloud].get(theme_name)
    if theme is None and cloud in user_themes.keys():
        theme = user_themes[cloud].get(theme_name)
    if theme is None:
        raise KeyError("Theme name not recognized")
    return theme


def _get_from_env(key):
    """Attempt to get a key from the environment, throwing an error if
    the key does not exist"""
    try:
        return os.environ[key]
    except:
        raise KeyError("Environment not configured properly.")


# ye olde argparse incantations
parser = argparse.ArgumentParser(description="wrapper around novaclient for"
                                 "launching clusters of OSDC systems.")
parser.add_argument("--quiet", "-q", action="store_true",
                    help="Run without logging.")

subparsers = parser.add_subparsers(help='subcommand should be one of '
                                   '[launch, delete]',
                                   dest="subcommand")

launch_parser = subparsers.add_parser("launch", help="launch a new cluster")
launch_parser.add_argument("number", type=int, help="number of compute nodes")
launch_parser.add_argument("--key", type=str,
                           help="location of the ssh key "
                                "to use for this cluster")
launch_parser.add_argument("--flavor", type=int,
                           help="the flavor ID to use for "
                                "the compute nodes")
launch_parser.add_argument("--theme", type=str,
                           help="name of a cluster theme "
                           "to use for this cluster.")
launch_parser.add_argument("--id", type=str,
                           help="the id to use for this cluster. "
                           "if none is passed, one will be generated"
                           "for you.")

list_parser = subparsers.add_parser("list", help="list all clusters.")

delete_parser = subparsers.add_parser("delete", help="delete a clusters.")
delete_parser.add_argument("cluster_id", type=str,
                           help="The id of the cluster to be deleted.")

# little logger class, just prints to stdout
class PrintLogger(object):
    def log(self, string):
        print string


def main():
    args = parser.parse_args()

    clientinfo = {
        "username": _get_from_env("OS_USERNAME"),
        "password": _get_from_env("OS_PASSWORD"),
        "auth_url": _get_from_env("OS_AUTH_URL"),
        "tenant_name": _get_from_env("OS_TENANT_NAME")
    }

    # determine cloud and cluster theme
    cloud = CLOUD_MAP.get(clientinfo["auth_url"])
    if cloud is None:
        raise RuntimeError("Your environment's Openstack Auth URL "
                           "is not known to correspond to any OSDC "
                           "system. Please make sure your environment "
                           "is configured correctly.")

    logger = PrintLogger() if not args.quiet else None

    if args.subcommand == "launch":

        # get a dictionary of theme information
        if args.theme is None:
            cluster_theme = _get_cluster_theme(cloud, "default")
        else:
            cluster_theme = _get_cluster_theme(cloud, args.theme)

        # launch the cluster
        nc.cluster_launch(cloud, clientinfo, args.number, cluster_theme,
                          args.flavor, os_key_name=args.key,
                          cluster_id=args.id,
                          logger=logger)

    elif args.subcommand == "list":
        for cluster_id in nc.list_clusters(clientinfo, logger=logger):
            print cluster_id

    elif args.subcommand == "delete":
        nc.delete_cluster(clientinfo, args.cluster_id, logger=logger)
