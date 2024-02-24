#!/usr/bin/env python3

import os
import docker
import netem_utilities
import netem_logging

logger = netem_logging.get_sublogger("clean_containers")

client = docker.from_env()

#
# Stop and remove a container
#
def stop_remove_container_byname(container_name):
    logger.info(f"Stopping and removing container {container_name}")
    containers = client.containers.list(all=True, filters={"name": container_name})
    if len(containers)==0:
        print("Can't find any containers that match filter.")
        return
    
    logger.info(f"Stopping {container_name}")
    try:
        containers[0].stop()
    except Exception as e:
        print(f"Can't stop container {container_name}")
        print(e)

    logger.info(f"Removing {container_name}")
    try:
        containers[0].remove()
    except Exception as e:
        print(f"Can't remove container {container_name}")
        print(e)


def disconnect_from_monitor_network(monitor_network, container_name):
    logger.info(f"Removing container {container_name} from monitor network.")
    try:
        containers = client.containers.list(all=True, filters={"name": container_name})
        monitor_network.disconnect(containers[0])
    except Exception as e:
        logger.info(f"Error removing container {container_name} from monitor network")


def cleanup_all():
    try:
        monitor_network = client.networks.get("monitor_default")
        netem_utilities.apply_to_all_containers(disconnect_from_monitor_network)
    except Exception as e:
        logger.info("No monitor network.")
    
    netem_utilities.apply_to_all_containers(stop_remove_container_byname)
    netem_utilities.remove_all_networks()


if __name__=="__main__":
    netem_logging.do_logging_config(os.getcwd())
    cleanup_all()
    
