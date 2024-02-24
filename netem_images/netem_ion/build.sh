#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

# translated into ion-open-source-${ION_VERSION} in the dockerfile
ION_VERSION=4.1.2

NO_CACHE=""
# uncomment to disable cache (redo apt update)
# NO_CACHE="--no-cache"
docker build ${NO_CACHE} --build-arg ION_VERSION=${ION_VERSION} -t netem_ion -f dockerfile .

