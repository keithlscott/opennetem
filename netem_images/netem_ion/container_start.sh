#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

#
# Singal handler to try to make the container stop faster.
# We kill off stuff here that we might have started.
#
function handle_ctrlc()
{
    kill -TERM $child_pid
    killall -9 collectd # We start this below
    killm               # Kill off ION
    exit
}

# trapping the SIGTERM signal
trap handle_ctrlc SIGTERM	# Docker stops containers wil SIGTERM

# /usr/sbin/collectd
/usr/sbin/collectd

tail -f /dev/null &
child_pid=$!

wait $child_pid

