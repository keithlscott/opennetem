#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#


# Singal handler to try to make the container stop faster.
# We kill off stuff here that we might have started.
#
function handle_signal()
{
    kill -TERM "$child" 2>/dev/null;

    killall -9 tail
    killall -9 collectd # We start this below
    exit 0
}

# trapping the SIGTERM (and other) signa(s)
trap handle_signal TERM INT KILL



# Now we start collectd.

# /usr/sbin/collectd
/usr/sbin/collectd

tail -f /dev/null &
child_pid=$!

wait $child_pid

