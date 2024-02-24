#!/bin/bash

docker network disconnect monitor statsd_exporter
sleep 1

docker stop statsd_exporter && docker rm statsd_exporter
sleep 1

docker run \
	--name statsd-exporter \
	--hostname statsd-exporter \
	--network monitor \
	-d -p 9102:9102 -p 9125:9125 -p 9125:9125/udp \
        -v $PWD/statsd/statsd_mapping.yml:/tmp/statsd_mapping.yml \
        prom/statsd-exporter --statsd.mapping-config=/tmp/statsd_mapping.yml

