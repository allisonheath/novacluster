# novacluster

A wrapper around the
[OpenStack nova client](https://github.com/openstack/python-novaclient)
for easy management of clusters on
[OSDC](http://www.opensciencedatacloud.org) systems.

## Installation

You'll need to have [setuptools](https://bitbucket.org/pypa/setuptools)
installed. I recommend using a [virtualenv](http://www.virtualenv.org/en/latest/),
which will come with setuptools.

```
$ git clone https://github.com/porterjamesj/novacluster.git
$ cd novacluster
$ python setup.py install
```

## Usage

Novacluster is similar to the
[python-novaclient](https://github.com/openstack/python-novaclient)
command line tool, but is used for managing entire TORQUE clusters rather
than individual machines. It requires the same environment variables to
be set as the `nova` command line tool. To set these up properly, please
see the Console > Settings > OpenStack API page of the could you are using.

Note that if you are working on a cloud login node, the environment has already
been configured for you. Also note that the OpenStack API for the protected data
clouds is accessible only from the login nodes, so you cannot use `nova` or
`novacluster` to manage your PDC projects directly from your own machine.
The API for Sullivan is accessible on public internet, so you can manage these
projects from anywhere.

### Launching clusters

Once your environment is configured, you can launch clusters using the
`novacluster launch` subcommand. At it's simplest, this command looks like:

```
$ novacluster launch 10
```

which will launch a cluster with 1 m1.medium head node and 10
m1.medium compute nodes. One of your keypairs will be chosen and
injected into each instances so that you can log in once they have launched.

Cluster launch is customizable by the following command line arguments:

#### `--id`

Specify an id for the cluster rather than having one generated for you.

#### `--key`

Specify which keypair you want injected into the cluster's instances.

#### `--flavor`

Specify which flavor of compute node you want. This should be the flavor ID,
which is a number. To see a description of each flavor ID you can run:

```
$ nova flavor-list
```

which should output something like:

```
+----+------------+-----------+------+-----------+------+-------+-------------+
| ID |    Name    | Memory_MB | Disk | Ephemeral | Swap | VCPUs | RXTX_Factor |
+----+------------+-----------+------+-----------+------+-------+-------------+
| 1  | m1.tiny    | 512       | 0    | 0         |      | 1     | 1.0         |
| 2  | m1.small   | 2048      | 20   | 0         |      | 1     | 1.0         |
| 3  | m1.medium  | 4096      | 20   | 0         |      | 2     | 1.0         |
| 4  | m1.large   | 8192      | 20   | 0         |      | 4     | 1.0         |
| 5  | m1.xlarge  | 16384     | 20   | 0         |      | 8     | 1.0         |
| 6  | m1.xxlarge | 32768     | 20   | 0         |      | 16    | 1.0         |
| 7  | m2.xxlarge | 65536     | 20   | 0         |      | 16    | 1.0         |
| 8  | m2.xlarge  | 32768     | 20   | 0         |      | 8     | 1.0         |
+----+------------+-----------+------+-----------+------+-------+-------------+
```

#### `--theme`

Specify a theme for the cluster. Described in detail in the next section.

### Cluster themes

novacluster allows for customization using cluster "themes".
A theme consists of of up to four things:

1. An image to use for head node.
2. An image to use for the compute nodes.
3. A script to be run at head node startup.
4. A script to be run at compute node startup.

You can specify anywhere from one to all four of these. Images can be specified
by any combination of name, id, and metadata.

Themes are described using [YAML](http://yaml.org/) in the configuration file
`~/.novacluster_themes`. For example, let's say you have a two images,
`my-headnode-image` and `my-computenode-image` in Sullivan and you want to
launch cluster from them. You would write the following in `~/.novacluster_themes`:

```yaml
sullivan:
  my-theme:
    compute: {name: my-compute-image}
    head: {name: my-head-image}
```

You could them launch a cluster from this theme with:

```
$ novacluster launch 10 --theme my-theme
```

As example, imagine that in the Bionumbus PDC, you have an image with
the metadata key `use_this_one` set to `true`, which you want to use
for both the head and compute nodes. Let's say you also have a script
at `/path/to/headnode_script` that you want to run on the headnode as
it starts up, and another script at `/path/to/computenode_script` that
you want run on the compute nodes as they startup. You would modify
your `~/.novacluster_themes` to look like the following:

```yaml
sullivan:
  my-theme:
    compute: {name: my-compute-image}
    head: {name: my-head-image}
pdc:
  second-theme:
    compute: {metadata: {use_this_one: true}}
    head: {metadata {use_this_one: true}}
    compute_script: /path/to/computenode_script
    head_script: /path/to/headnode_script
```

With your environment set up for the PDC, you could then launch a
cluster with these specifications using:

```
$ novacluster launch 10 --theme second-theme
```

#### Notes on theme creation

When creating a theme, it is important to keep in mind that the image
you use for the head node must have the TORQUE cluster management
software installed on it in order for your clusters to work
properly. The default head node image, which is named
"Ubuntu-12.04-LTS-v1.4-TorqueHN-20130729" has this software
preinstalled.  For this reason we recommend that if you want to use
a custom headnode image, you should do the following:

1. Start a new instance of the basic TorqueHN image
2. Make the modifications you need
3. Snapshot the running instance, [making sure the snapshot is consistent](http://docs.openstack.org/trunk/openstack-ops/content/consistent_snapshots.html)
4. Specify the snapshot as your headnode image.

### Listing running clusters

You can see a list of the ids of all clusters your have running with:

```
$ novacluster list
```

### Deleting clusters

Let's say you have a cluster with id `my-cluster` that you don't need anymore,
you can delete it using:

```
$ novacluster delete my-cluster
```
