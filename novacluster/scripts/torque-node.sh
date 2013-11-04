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
sudo %(node_script)s

# run custom user script
user_script="%(user_script)s"
if [ user_script != None ]
then
    echo "user_script" | base64 --decode > /tmp/user_script
    sudo chmod a+x /tmp/user_script
    sudo /tmp/user_script
fi

echo "test" > /tmp/worked
