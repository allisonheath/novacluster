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

# put keys in place
if ! %(pdc)s
then
    echo "Host torque-headnode-$CLUSTER_ID*" >> /home/ubuntu/.ssh/config
    echo "    StrictHostKeyChecking no" >> /home/ubuntu/.ssh/config
    echo "    UserKnownHostsFile=/dev/null" >> /home/ubuntu/.ssh/config
    echo %(public_key)s >> /home/ubuntu/.ssh/authorized_keys
    echo "%(private_key)s" > /home/ubuntu/.ssh/id_dsa
    chown ubuntu:ubuntu /home/ubuntu/.ssh/id_dsa
    chmod 600 /home/ubuntu/.ssh/id_dsa
fi

while ! ping -c 1 torque-headnode-$CLUSTER_ID
do
    sleep 1
done

sudo %(node_script)s

echo "node script" >> /tmp/worked

# run custom user script
user_script=`echo "%(user_script)s" | base64 --decode`
if [[ $user_script != None ]]
then
    echo $user_script > /tmp/user_script
    sudo chmod a+x /tmp/user_script
    sudo /tmp/user_script
fi

echo "user script" >> /tmp/worked
