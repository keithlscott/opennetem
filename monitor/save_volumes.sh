#!/bin/bash

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

#
# This shell script saves the docker volume data from the Grafana,
# Prometheus, and influxDB containers to .tgz files.
#
# The restore_volumes.sh script can be used to restore them, e.g.
# when doing a new installation.
#

# https://docs.docker.com/storage/volumes/#back-up-restore-or-migrate-data-volumes

echo "Backing up grafana volume..."
docker run -v /monitor_grafana-data --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from monitor-grafana-1 -v    $(pwd):/backup busybox tar czf /backup/grafana-data.tgz /var/lib/grafana
docker rm dbstore2

echo "Backing up prometheus volume..."
docker run -v /monitor_prometheus-data --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from monitor-prometheus-1 -v $(pwd):/backup busybox tar czf /backup/prometheus-data.tgz /prometheus
docker rm dbstore2

echo "Backing up influxDB volume..."
docker run -v /monitor_influxdb-data --name dbstore2 ubuntu /bin/bash
docker run --rm --volumes-from monitor-influxdb-1 -v   $(pwd):/backup busybox tar czf /backup/influxdb-data.tgz /var/lib/influxdb2
docker rm dbstore2




