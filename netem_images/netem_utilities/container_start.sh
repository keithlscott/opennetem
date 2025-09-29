#!/bin/bash
# /usr/sbin/collectd

/usr/local/bin/reltime_server.py >& /dev/null &

#
# Singal handler to try to make the container stop faster.
# We kill off stuff here that we might have started.
#
function handle_signal()
{
    echo "I'm in the signal handler."

    echo `date` >> /usr/local/netem_utilities/start_container.log
    echo "in handle_ctrlc" >> /usr/local/netem_utilities/start_container.log

    kill -TERM "$child" 2>/dev/null;

    killall -9 tail
    killall -9 collectd # We start this below
    killall -9 reltime_server.py
    sync ; sync
    exit 0
}

# trapping the SIGTERM (and other) signa(s)
trap handle_signal TERM INT KILL


LOG_FILE=/usr/local/netem_utilities/start_container.log

echo `date`        > $LOG_FILE
echo "Starting"   >> $LOG_FILE
echo "Processes"  >> $LOG_FILE
echo `ps auxww`   >> $LOG_FILE
echo "Traps"      >> $LOG_FILE
echo `trap -p`    >> $LOG_FILE


tail -f /dev/null &
child_pid=$!

wait $child_pid
