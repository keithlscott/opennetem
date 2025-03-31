#!/bin/bash

#
# For monitoring stack
#
echo "Pulling monitoring stack images from docker.hub..."
docker pull grafana/grafana-enterprise
docker pull prom/collectd-exporter
docker pull prom/prometheus
docker pull prom/statsd-exporter
docker pull influxdb

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
