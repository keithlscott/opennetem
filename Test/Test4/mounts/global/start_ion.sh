#!/bin/bash
#LOG="/netsim/mounts/node_a/start_ion.log"
#NODE_NAME="n1"
LOG="start_ion2.log"

echo "" > $LOG

if [ -f ion.env ]; then
	echo "Using environment information from ion.env."
	source ion.env
else
	echo "No environment information; NODE_NAME and LOG are likely unset."
fi

if [ -z ${NODE_NAME} ]; then
	echo "NODE_NAME not set; need to set NODE_NAME and LOG (log file name)"
	exit -1
else
	echo "Node name is set to:" ${NODE_NAME}
fi

# Start ION
echo "Starting ION at `date`" >> $LOG
if [ -f ${NODE_NAME}.ionrc ]; then
	echo "Running ionadmin ${NODE_NAME}.ionrc" >> $LOG
	ionadmin ${NODE_NAME}.ionrc
else
	echo "Big problem; no ionrc file; exiting."
	exit -1
fi

sleep 1

if [ -f $NODE_NAME\.ionsecrc ]; then
	echo "Running ionsecadmin on ${NODE_NAME}.ionsecrc" >> $LOG
	ionsecadmin ${NODE_NAME}.ionsecrc
else
	echo "No ionsecrc file ${NODE_NAME}.ionsecrc" >> $LOG
fi

if [ -f ${NODE_NAME}.ltprc ]; then
	ltpadmin ${NODE_NAME}.ltprc
else
	echo "No ltprc file ${NODE_NAME}.ltprc" >> $LOG
fi

sleep 1

if [ -f ${NODE_NAME}.bprc ]; then
	echo "Running bpadmin on ${NODE_NAME}.bprc" >> $LOG
	bpadmin ${NODE_NAME}.bprc
else
	echo "No bprc file ${NODE_NAME}.bprc" >> $LOG
fi

# bprc will run ipnadmin

sleep 5

if [ -f $NODE_NAME\.imcrc ]; then
	echo "Running imcadmin on $NODE_NAME\.imcrc" >> $LOG
	imcadmin $NODE_NAME\.imcrc
fi

if [ -f $NODE_NAME\.cfdprc ]; then
	echo "Running cfdpadmin on $NODE_NAME\.cfdprc" >> $LOG
	cfdpadmin $NODE_NAME\.cfdprc
else
	echo "No cfdprc file for $NODE_NAME" >> $LOG
fi

# if [ -f ../global/contacts.ionrc ]; then
# 	echo "Running ionadmin on contacts file contacts.ionrc." >> $LOG
# 	ionadmin ../global/contacts.ionrc
# else
# 	echo "No contacts.ionrc file right now." >> $LOG
# fi

#echo "Staring bpecho on 1.1" >> $LOG
#nohup bpecho ipn:${NODE_NUMBER}.1 >&/dev/null &

sleep 3
