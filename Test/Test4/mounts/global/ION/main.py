#!/usr/bin/env python3

import sys
import json
import ION
import logging
import logging.config
import argparse
import datetime

logger = logging.getLogger()
logger.handlers.clear()

logging.basicConfig(
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler("ion_config_tool.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger()


def test1():
    foo = ION.ion_node("name", 7)

    foo.add_outduct("ltp", 1, "10.99.00.3")
    foo.add_outduct("udp", 44, "10.99.99.42")

    foo.write_configs()


def networks_of_node(container_info, node_name):
        my_networks = []

        # See what neighbors we have
        for interface in container_info[node_name]:
            if "network_name" in interface:
                my_networks += [interface["network_name"]]
        return(my_networks)


def node_name_from_number(ion_configs, peer_node_number):
    for ic in ion_configs:
        print(ic)
        ion_config = ion_configs[ic]
        print(ion_config)
        if ion_config[1].node_number==peer_node_number:
            return ion_config[1].node_name
    logger.warning("Can't find node name for node number {peer_node_number}")
    sys.exit(0)

def addr_of_my_neighbor(container_info, my_name, neighbor_name):
    my_networks = networks_of_node(container_info, my_name)
    for interface in container_info[neighbor_name]:
        if "network_name" not in interface:
            continue
        if interface["network_name"] in my_networks:
            print(interface)
            return(interface["addr_info"][0]['local'])
    return(None)


def addr_of_node_on_network(container_info, node_name, net_name):
    for net in container_info[node_name]:
        if "network_name" not in net:
            continue
        if net["network_name"]==net_name:
            return net["addr_info"][0]["local"]  # NEEDS HELP

def node_number_of(ion_configs, node_name):
    for ic in ion_configs:
        if ion_configs[ic][0]==node_name:
            return(ic)
    logger.warning(f"Can't find ion node number for node: {node_name}")
    logger.warning(f"ion_configs is: {ion_configs}")
    return(None)

    
def make_ion_configs(scenario_info, container_info, args):
    ion_configs = {}   # Keyed by node_number, values are (node_name, ION.ion_node instance tuples)
    next_auto_ion_node_number = 400000

    if True:
        global_config = scenario_info["node_configs"]["__global"] if "__global" in scenario_info["node_configs"] else {}
        for node in scenario_info["node_configs"]:
            if node=="__global":
                continue
            # Merge in global_config info with current node config
            scenario_info["node_configs"][node].update(global_config)
    
    #
    # Run through all the nodes in the scenario; crate ION instances
    # and fill in ion node numbers.
    #
    for node in scenario_info["node_configs"]:
        this_node = scenario_info["node_configs"][node]
        logger.info(f"this_node is {this_node}")
        if node=="__global":
            continue
        if "ion_config" not in scenario_info["node_configs"][node]:
            logger.info(f"no ion_config in node {this_node} info")
            continue

        logger.info(f"ion_config for node {node} is {this_node['ion_config']}")
        if "output_dir" in this_node["ion_config"]:
            output_dir = this_node["ion_config"]["output_dir"] if "output_dir" in this_node["ion_config"] else f""

        if "node_number" in this_node["ion_config"]:
            the_ion_node_number = this_node["ion_config"]["node_number"]
        else:
            the_ion_node_number = next_auto_ion_node_number
            next_auto_ion_node_number += 1

        if the_ion_node_number not in ion_configs:
            ion_configs[the_ion_node_number] = (node, ION.ion_node(node, the_ion_node_number))  # node here is the node name
            logger.info(f"Making ion_node instance for {node}")

        if "config_dir" in this_node["ion_config"]:
            ion_configs[the_ion_node_number][1].output_directory = this_node["ion_config"]["config_dir"]

    logger.info(f"Done making initial ION instances ({len(ion_configs)}).")

    # Now we have (mostly blank) ION.ion_node instances for the ION nodes
    # and the mapping of those to container node names.  Now we need to
    # figure out who's connected to who.
    neighbor_nodes = {}  # Keyed by node name, value is list of tuples (container_node_info, network_name, address)

    for node in ion_configs:
        node_name = ion_configs[node][0]
        ion_config = ion_configs[node][1]
        print(f"Looking at node {node_name} for neighbors.")
        print(f"ion_configs[node] is {ion_configs[node]}")

        logger.info(f"Adding 'loopack' udp induct to node {node_name}")
        ion_config.add_induct("udp")   # Everybody gets a UDP loopback CLA

        my_networks = networks_of_node(container_info, node_name)

        #
        # Now find other nodes that share networks with me
        #
        for container_node in container_info:
            # Add a UDP loopback convergence layer to self.
            if container_node == node_name:
                logger.info(f"Adding UDP loopback for {node_name}")
                ion_config.add_outduct("udp", ion_config.node_number, "127.0.0.1", node_name)
                continue
            
            logger.info(f"Considering container_node {container_node} as potential neighbor")
            for interface in container_info[container_node]:
                if "network_name" not in interface:
                    continue

                logger.info(f"container {container_node} interface {interface['ifname']} on network {interface['network_name']}")
                if interface["network_name"] in my_networks:
                    # I share a network with this neighbor; need to work both
                    # my and his configurations to add appropriate CLAs in each
                    # direction
                    logger.info(f"node {node_name} shares a network with node {container_node} :: {interface['network_name']}")
                    if node_name not in neighbor_nodes:
                        neighbor_nodes[node_name] = []
                    neighbor_nodes[node_name] += [[container_node, interface["network_name"], addr_of_node_on_network(container_info, container_node, interface["network_name"])]]
                    logger.info(f"^^^^^^ neighbor_nodes[{node_name}] is now: {neighbor_nodes[node_name]}")
    logger.info("######################")
    for node_name in scenario_info['node_configs']:
        if node_name=="__global":
            continue
        my_ion_config = None
        for ic in ion_configs:
            if ion_configs[ic][0]==node_name:
                my_ion_config = ion_configs[ic][1]
        

        # If I have no explicit outducts specified, generate one UDP outduct to each neighbor
        if "ion_config" not in scenario_info["node_configs"][node_name]:
            logger.info(f"no ion_config in {node_name}")
            logger.info(f"{scenario_info['node_configs'][node_name]}")
            continue

        if "outducts" not in scenario_info["node_configs"][node_name]["ion_config"]:
            logger.info(f"#### node {node_name} has no explicit outducts, adding UDP outducts to neighbors on networks: {neighbor_nodes[node_name]}")
            # neighbor_nodes is a list [[container_node, network_name, address_of_node_on_network]]
            for gloop in neighbor_nodes[node_name]:
                logger.info(f"Adding UDP outduct to node {node_name}'s config to addr: {gloop[2]}")
                peer_node_number = node_number_of(ion_configs, gloop[0])
                peer_node_name = node_name_from_number(ion_configs, peer_node_number)
                my_ion_config.add_outduct("udp", peer_node_number, gloop[2], peer_node_name)

                print(f"trying to find ic for {peer_node_number}")
                print(f"{ion_configs[ic][1]}")
                for ic in ion_configs:
                    if ion_configs[ic][1].node_number==peer_node_number:
                        their_ion_config = ion_configs[ic][1]
                their_ion_config.add_induct_peer(my_ion_config.node_number)

        else:
            logger.info(f"#### node {node_name} has explicit outducts: {scenario_info['node_configs'][node_name]['ion_config']['outducts']}")
            for outduct in scenario_info["node_configs"][node_name]["ion_config"]["outducts"]:
                logger.info(f"Adding {outduct[1]} outduct from {node_name} to {outduct[0]}")
                peer_node_number = node_number_of(ion_configs, outduct[0])
                my_ion_config.add_outduct(outduct[1], peer_node_number, addr_of_my_neighbor(container_info, node_name, outduct[0]), outduct[0])
                logger.info(f"Adding {outduct[1]} induct to {outduct[0]}")
                their_ion_config = None
                for ic in ion_configs:
                    if ion_configs[ic][0]==outduct[0]:
                        their_ion_config = ion_configs[ic][1]
                their_ion_config.add_induct(outduct[1])
                their_ion_config.add_induct_peer(my_ion_config.node_number)

    logger.info(f"Now writing config files for: {args.write_configs}")
    for node in ion_configs:
        node_name =  ion_configs[node][0]
        ion_config = ion_configs[node][1]
        if node_name not in args.write_configs:
            continue
        ion_config.write_configs()

    return

def main():
    logger.info("Starting")

    parser = argparse.ArgumentParser()
    parser.add_argument("--config_dir", "-c", default="/netem/globals/")
    parser.add_argument("--write-configs", "-w", nargs="+", default=[], action="append")  # node names
    parser.add_argument("--base_dir", "-b", default=None)  # Base directory for ION config files
    args = parser.parse_args()
    logger.info(f"args are {args}")
    args.write_configs = [x[0] for x in args.write_configs]

    if args.write_configs == []:
        logger.warning("Not writing any configs")

    try:
        with open(f"{args.config_dir}/scenario.json", "r") as fp:
            data = fp.read()
            scenario_info = json.loads(data)
        
        with open(f"{args.config_dir}/container_info.json", "r") as fp:
            data = fp.read()
            container_info = json.loads(data)
    except Exception as e:
        logger.warning(f"Can't open one of scenario.json, container_info.json from {args.config_dir}")
        sys.exit(0)

    make_ion_configs(scenario_info, container_info, args)

if __name__=="__main__":
    main()
