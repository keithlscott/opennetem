#!/bin/bash

# docker run --rm --name statsd -v $PWD/config.js:/usr/src/app/config.js -p 8125:8125/udp -p 8126:8126 statsd/statsd

docker run \
	--name statsd \
	--ip 172.18.0.1 \
	--network monitor \
	-v $PWD/statsd/config.js:/usr/src/app/config.js \
	-d --p8125:8125 -p 8126:8126 \
	statsd

