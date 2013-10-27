#!/bin/bash
CLUSTER_ID=%(cluster_id)s

if %(pdc)s
then
    if [ `whoami` != "%(username)s" ]
    then
        exit 1
    fi
fi

# wait for gluster to come up
#while ! ls /glusterfs/users/torque_nodes/setup_scripts/
while ! ls /glusterfs/
do
    sleep 1
done

CONF_FILE=/tmp/torque_config
TORQ_CONF_FILE=/tmp/torque_config2
echo -ne '$pbsserver  ' > $CONF_FILE
echo "torque-headnode-$CLUSTER_ID" >> $CONF_FILE
echo '$logevent      225' >> $CONF_FILE
echo '$usecp *:/glusterfs/users /glusterfs/users' >> $CONF_FILE
echo '$loglevel 4' >> $CONF_FILE

echo '/etc/local/lib/' > $TORQ_CONF_FILE

# Using a security flaw here w e will need to change this
#sudo /tmp/setup_nodes.sh
#sudo /glusterfs/users/torque_nodes/headnode/tukey_node.sh
echo "test" > /tmp/worked
sudo %(node_script)s
