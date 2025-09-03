
#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

start_time=`cat /netem/globals/instance_info.json | jq '.start_time'`

cur_time=`date +"%s"\ | sed -e "s/\..*//"`


delta_time=$(expr $cur_time - $start_time)
echo $delta_time $*

