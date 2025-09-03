#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

SOURCE=$1
DEST=$2
start_time=$3

#start_time=`cat ../Test/Test3/netsim/globals/instance_info.json | jq '.start_time' | sed -e "s/\..*//"`
#echo "start_time is $start_time"

# ping -4 www.google.com | while read pong; do echo "$(date) ==== $(expr $(date +"%s") - $start_time): $pong"; done

bping ${SOURCE} ${DEST} | while read pong; do echo "$(date) ==== $(expr $(date +"%s") - $start_time): $pong"; done



