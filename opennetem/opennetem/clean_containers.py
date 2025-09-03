#!/usr/bin/env python3

import os
import docker
import opennetem.utilities as utilities
import opennetem.my_logging as my_logging

logger = my_logging.get_sublogger("clean_containers")

client = docker.from_env()

#
# Stop and remove containers by label
#
# Container_label list should be of the form ["opennetem_node=True", ...
#]
def stop_remove_container_bylabel(container_label_list):
    containers = client.containers.list(all=True, filters={"label": container_label_list})
    if len(containers)==0:
        print(f"Can't find any containers that match filter 'label: {container_label_list}.")
        return

    for c in containers:
        stop_remove_container_byname(c.name)
    
    return


#
# Stop and remove a container
#
def stop_remove_container_byname(container_name):
    logger.info(f"Stopping and removing container {container_name}")
    containers = client.containers.list(all=True, filters={"name": container_name})
    if len(containers)==0:
        print("Can't find any containers that match filter.")
        return
    
    logger.debug(f"Stopping {container_name}")
    try:
        containers[0].stop()
    except Exception as e:
        logger.warning(f"Can't stop container {container_name} {e}")

    logger.debug(f"Removing {container_name}")
    try:
        containers[0].remove()
    except Exception as e:
        logger.warning(f"Can't remove container {container_name} {e}")

def disconnect_from_monitor_network(monitor_network, container_name):
    logger.debug(f"Removing container {container_name} from monitor network.")
    try:
        containers = client.containers.list(all=True, filters={"name": container_name})
        monitor_network.disconnect(containers[0])
    except Exception as e:
        logger.debug(f"Error removing container {container_name} from monitor network")


def cleanup_all():
    logger.info("Cleanup_all()")
    try:
        monitor_network = client.networks.get("monitor_default")
        utilities.apply_to_all_containers(disconnect_from_monitor_network)
    except Exception as e:
        logger.info("No monitor network.")
    
    utilities.apply_to_all_containers(stop_remove_container_byname)
    utilities.remove_all_networks()


if __name__=="__main__":
    my_logging.do_logging_config(os.getcwd())
    cleanup_all()
    
