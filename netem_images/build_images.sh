#!/bin/bash

#
# Monitoring stack images will be pulled when docker compose up
# is run in the monitor directory.
#echo "Pulling monitoring stack images from docker.hub..."
# docker pull grafana/grafana-enterprise:12.1
#docker pull prom/collectd-exporter
#docker pull prom/prometheus
#docker pull prom/statsd-exporter
#docker pull influxdb:2.7.12

OPENNETEM_IMAGE_DIRS="netem1 netem_ion netem_utilities"

echo "Building opennetem node images."
pushd .
for dir in $OPENNETEM_IMAGE_DIRS; do
	pushd .
	cd $dir
	./build.sh
	cd ..
	popd
done
popd
