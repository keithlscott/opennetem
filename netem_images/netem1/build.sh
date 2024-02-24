#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

NO_CACHE=""
# uncomment to disable cache (redo apt update)
# NO_CACHE="--no-cache"
docker build ${NO_CACHE} -t netem1 .

