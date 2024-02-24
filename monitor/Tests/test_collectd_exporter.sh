#!/bin/bash

docker network disconnect monitor collectd-exporter

docker stop collectd-exporter && docker rm collectd-exporter

docker run \
	-d \
	--hostname collectd-exporter \
	-p 25826:25826 \
	--name collectd-exporter \
	prom/collectd-exporter \
	--collectd.listen-address=":25826"

docker network connect monitor collectd-exporter

