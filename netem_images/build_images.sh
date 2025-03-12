#!/bin/bash

#
# For monitoring stack
#
docker pull grafana/grafana-enterprise
docker pull prom/collectd-exporter
docker pull prom/prometheus
docker pull prom/statsd-exporter
docker pull influxdb


pushd .
cd netem1
./build.sh
cd ..

cd netem_frr
docker pull quay.io/frrouting/frr:master
./build.sh
cd ..

cd netem_ion
./build.sh
cd ..

cd netem_utilities
./build.sh
cd ..
popd
