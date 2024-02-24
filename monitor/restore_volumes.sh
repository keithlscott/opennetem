#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

#
# This script resotres the contents of the Grafana, Prometheus, and
# influxDB container volumes.
#

GRAFANA_VOLUME_NAME=monitor_grafana-data

echo "Restoring grafana-data..."
docker volume rm ${GRAFANA_VOLUME_NAME}
docker rm dbstore2
docker run -v ${GRAFANA_VOLUME_NAME}:/var/lib/grafana --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from dbstore2 -v $(pwd):/backup ubuntu bash -c "cd / && tar xzvf /backup/grafana-data.tgz"
docker rm dbstore2

PROM_VOLUME_NAME=monitor_prometheus-data

echo "Restoring prometheus-data..."
docker volume rm ${PROM_VOLUME_NAME}
docker rm dbstore2
docker run -v ${PROM_VOLUME_NAME}:/prometheus --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from dbstore2 -v $(pwd):/backup ubuntu bash -c "cd / && tar xzvf /backup/prometheus-data.tgz"
docker rm dbstore2

INFLUXDB_VOLUME_NAME=monitor_influxdb-data

echo "Restoring influxdb-data..."
docker volume rm ${INFLUXDB_VOLUME_NAME}
docker rm dbstore2
docker run -v ${INFLUXDB_VOLUME_NAME}:/var/lib/influxdb2 --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from dbstore2 -v $(pwd):/backup ubuntu bash -c "cd / && tar xzvf /backup/influxdb-data.tgz"
docker rm dbstore2




