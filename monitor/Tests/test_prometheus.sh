#!/bin/bash

docker network disconnect monitor prometheus
sleep 1

docker stop prometheus && docker rm prometheus
sleep 1

# Create persistent volume for your data
# docker volume create prometheus-data
# Start Prometheus container
docker run \
    -d \
    --name prometheus \
    --hostname prometheus \
    --network monitor \
    -p 9090:9090 \
    -v /home/kscott/Projects/netem/monitor/prometheus:/etc/prometheus/ \
    -v prometheus-data:/prometheus \
    prom/prometheus \
    --config.file=/etc/prometheus/prometheus.yml \
    --storage.tsdb.path=/prometheus \
    --web.console.libraries=/usr/share/prometheus/console_libraries \
    --web.console.templates=/usr/share/prometheus/consoles \
    --web.enable-admin-api
sleep 1

