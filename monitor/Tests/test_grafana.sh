#!/bin/bash

echo "Stopping and removing 'grafana' container."
docker stop grafana && docker rm grafana
sleep 1

echo "Removing 'grafana' from the monitor network'"
docker network disconnect monitor grafana
sleep 1

echo "Running new grafana container."
docker run \
	-d -p 3000:3000 \
	--hostname grafana \
	--network monitor \
	--name=grafana \
        -v grafana-data:/var/lib/grafana \
	grafana/grafana-enterprise
sleep 1

echo "Attaching grafana to monitor network."
docker network connect monitor grafana


