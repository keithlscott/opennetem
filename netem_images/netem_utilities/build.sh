#!/bin/bash

NO_CACHE=""
# uncomment to disable cache (redo apt update)
# NO_CACHE="--no-cache"
docker build ${NO_CACHE} -t netem_utilities .
