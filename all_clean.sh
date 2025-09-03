#!/usr/bin/bash

# This script attempts to remove all traces of an opennetem installation
#   - The running instances
#   - The Python virtual environment in this directory
#   - The docker images used for the virtual machines

# WARNING
# We have no way of knowing if the infrastructure images (e.g. influxdb, grafana)
# were added to support opennetem or if they were already present on the system
# and used by something else.
IMAGES_TO_REMOVE="netem1 netem_ion netem_utilities \
	quay.io/frrouting/frr:master \
	prom/prometheus prom/collectd-exporter prom/statsd-exporter \
	influxdb \
	grafana/grafana-enterprise"

VOLUMES_TO_REMOVE="monitor_influxdb-data monitor_grafana-data monitor_prometheus-data"

# Remove the Python virtual environment
echo "Removing Python virutal environment directory (./venv)."
rm -rf ./venv

echo "Removing executables from /usr/local/bin (with sudo)"
EXECUTABLES="/usr/local/bin/opennetem /usr/local/bin/on_mon_rtt /usr/local/bin/on_bplist /usr/local/bin/on_bpstats"
for item in $EXECUTABLES; do
	sudo /bin/rm -f $item
done


# Remove running opennetem node instances
#
# Find all docker nodes with label 'opennetem_node' == True
# and remove them
nodes=`docker ps -a --filter "label=opennetem_node=True" | awk '{print $NF}' | tail -n "+2"`
echo "Nodes:"
for n in $nodes; do
	echo "Removing opennetem node $n"
	docker stop $n && docker rm $n &
done

# Wait for backgrounded node stop jobs to finish
wait


# Remove Monitoring Insfrastructure


# Try this first; we'll use lower-level docker commands later in case docker-compose
# isn't installed / running right.
echo "Trying docker-compose down to remove monitoring infrastructure."
cd monitor
docker-compose down


# Remove running opennetem node instances
#
# Find all docker nodes with label 'opennetem_node' == True
# and remove them
nodes=`docker ps -a --filter "label=opennetem_monitor_node=True" | awk '{print $NF}' | tail -n "+2"`
echo "Nodes:"
for n in $nodes; do
	echo "Removing opennetem node $n"
	docker stop $n && docker rm $n &
done

# Wait for backgrounded node stop jobs to finish
wait

# Remove docker volumes used by monitoring
for volume in $VOLUMES_TO_REMOVE; do
	docker volume rm $volume
done

# Remove opennetem networks
#
# Do this after nodes
#
# Find all docker networks with label 'opennetem_network' == True
# and remove them
networks=`docker network ls --filter "label=opennetem_network=True" | awk '{print $2}' | tail -n "+2"`
echo "'Regular' (node) Networks:"
for n in $networks; do
	echo "Removing opennetem network $n"
	docker network rm $n
done

networks=`docker network ls --filter "label=opennetem_monitor_network=True" | awk '{print $2}' | tail -n "+2"`
echo "Monitoring Networks:"
for n in $networks; do
	echo "Removing opennetem network $n"
	docker network rm $n
done
echo ""



# Remove docker images
#
# See WARNING top of file
#
echo "Will remove docker images:"
echo $IMAGES_TO_REMOVE

read -p "Continue? (Y/N): " confirm && [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]] || exit 1

# Remove docker images
for image in ${IMAGES_TO_REMOVE}; do
	echo "Removing docker image: $image"
	docker image rm $image
done

