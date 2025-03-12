#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

#
# time_variant_topology class for dealing with time-variant topologies
#   - Read topology from .xlsx file / sheet
#
# 
import sys
import math
import docker

import json
import logging
import pandas
import numpy
import argparse
import subprocess
import ipaddress

import opennetem.scenario

import logging
import opennetem.my_logging as my_logging

# logger = my_logging.get_sublogger("topology")
logger = logging.getLogger("opennetem.topology")

class netem_link(object):
    def __init__(self, source, dest, owlt_s, bandwidth_bps):
        self.source = source
        self.dest = dest
        self.owlt_s = owlt_s
        self.bandwidth_bps = bandwidth_bps
        return

    def __to_json__(self):
        ret = {}
        ret["owlt"] = self.owlt_s
        ret["data_rate_bps"] = self.data_rate_bps
        return(json.dumps(ret))


class time_variant_topology(object):
    def __init__(self, scenario):
        self.df = None
        self.scenario = scenario
        self.iface_info = None
        return

    # Subnet of the form '192.168.44.0/24'
    # Gateway of the form '192.168.44.254'
    def create_network(self, subnet, gateway, net_name):
        logger.info(f"Instantiating network {net_name} with as {subnet} with gateway {gateway}")
        ipam_pool = docker.types.IPAMPool(
            subnet=subnet,
            gateway=gateway
        )
        ipam_config = docker.types.IPAMConfig(
            pool_configs=[ipam_pool]
        )
        network = self.scenario.client.networks.create(
            net_name,
            driver="bridge",
            labels={"netem_network": "True"},
            ipam=ipam_config
        )
        return(network)
    

    def read_topofile(self, filename=None, sheetname=None):
        if filename==None and self.scenario!=None:
            logger.info("Getting topology file from scenario {self.scenario.filename}.")
            filename = self.scenario.scenario_dict["topology_filename"]
            if "topology_sheetname" in self.scenario.scenario_dict:
                sheetname = self.scenario.scenario_dict["topology_sheetname"]
        elif filename!=None:
            pass
        else:
            logger.critical("No filename or scenario to identify topofile.")

        if filename.find(".xlsx")>=0:
            self.df = pandas.read_excel(filename, sheetname)
        elif filename.find(".json")>=0:
            self.df = self.read_topofile_json(filename)
        elif filename.find(".csv")>=0:
            self.df = pandas.read_csv(filename)

        # Strip whitespace from column names
        self.df.columns = self.df.columns.str.strip()
    
        # Strip whitespace from values
        # self.df = self.df.applymap(lambda x: x.strip().rstrip() if isinstance(x, str) else x)
        self.df = self.df.map(lambda x: x.strip().rstrip() if isinstance(x, str) else x)

        # Replace all empty elements with NaN
        self.df.replace('', numpy.nan, inplace=True)

        # Drop any column that seems to be a comment
        for to_drop in ["comments", "comment", "Comments", "Comment"]:
            if to_drop in self.df:
                self.df.drop(columns=to_drop, inplace=True)

        # Convert all column names to lower case
        self.df.columns = self.df.columns.str.lower()

        logger.debug(f"After converting to lower self.df is:")
        tmp = str(self.df)
        tmp_lines = tmp.split("\n")
        for l in tmp_lines:
            logger.debug(l)

        self.fill_topo_df()
    

    # Fill in elided topology columns elements as needed
    # df["col"][row_indexer] = value
    #
    # Use `df.loc[row_indexer, "col"] = values` instead, to perform the assignment in a single step and ensure this keeps updating the original `df`.

    def fill_topo_df(self):
        cur_time = None

        for index, row in self.df.iterrows():
            try:
                if pandas.isnull(row["time"]):
                    #self.df["time"][index] = cur_time
                    self.df.loc[index, "time"] = cur_time
                else:
                    cur_time = row["time"]
                    cur_source = None
                    cur_dest = None

                if pandas.isnull(row["source"]):
                   # self.df["source"][index] = cur_source
                   self.df.loc[index, "source"] = cur_source
                else:
                    cur_source = row["source"]

                if pandas.isnull(row["dest"]):
                    # self.df["dest"][index] = cur_dest
                    self.df.loc[index, "dest"] = cur_dest
                else:
                    cur_dest = row["dest"]
            except Exception as e:
                logger.fatal(f"Can't fill_topo_df for row {row}")
                sys.exit(0)
                
        logger.debug(f"\n{self.df}")


    def read_topofile_json(self, filename):
        with open(filename, "r") as fp:
            data = fp.read()
            info = json.loads(data)

        new_dict_list = []

        for timestep in info:
            cur_time = timestep["time"]
            for e in timestep["link_changes"]:
                cur_line = {"time": cur_time}
                if "dest" in e:
                    cur_line.update(e)
                    new_dict_list += [cur_line]
                elif "dests" in e:
                    for e2 in e["dests"]:
                        cur_line = {"time": cur_time, "source": e["source"]}
                        cur_line.update(e2)
                        new_dict_list += [cur_line]
                    
        df = pandas.DataFrame(new_dict_list)

        return(df)


    # Return a list of the interfaces on the host that are associated
    # with the given bridge.
    def get_host_interfaces_of_bridge(self, bridge):
        foo = subprocess.run(f"/usr/sbin/brctl show {bridge}".split(), capture_output=True)
        output = foo.stdout.decode("utf-8")
        lines = output.split("\n")
        ret = []
        for l in lines[1:3]:
            toks = l.split()
            ret += [toks[-1]]
        return(ret)


    #
    # Build a dictionary of information that allows mapping a node pair
    # like node1 -> node2 into the host veth interfaces so that we can
    # know which veth interfaces on the host to tinker with using tc
    # to affeect the link characteristics
    #
    def build_interface_mapping(self, network):
        #foo = self.scenario.client.networks.list(names=[network_name])
        all_results = []
        
        # logging.info(f"in build_interface_mapping network is {network}.")
        host_res = subprocess.run("ip --json addr show".split(), capture_output=True)
        tmp = host_res.stdout.decode("utf-8")
        host_info = json.loads(tmp)

        network.reload()  # See https://github.com/docker/docker-py/issues/1775
        bar = self.get_host_interfaces_of_bridge(f"br-{network.short_id}")
        # print(f"host interfaces of bridge br-{net.short_id} are: {bar}")

        # Build a list of acceptable host interfaces for this bridge
        info_list = []
        t1 = []
        for e in host_info:
            if e["ifname"] in bar:
                t1 += [[e["ifname"], e["ifindex"]]]
                info_list += [e.copy()]

        # print(f"t1 for br-{net.short_id} is\n{t1}")
            
        for c in network.containers:
            # print(f"Examining container {c.name}")
            out = c.exec_run("ip --json addr show")
            output = out.output.decode("utf-8")
            try:
                info = json.loads(output)
            except Exception as e:
                print(f"Can't get addr info for container {c.name}")
                continue
            # print(json.dumps(info, indent=2))
            # self.scenario.container_info[c.name] = info

            # Add container names
            for container_interface in info:
                # if "link_index" in container_interface:
                #     print(f"Looking for link_index {container_interface['link_index']}")
                for ttt in t1:
                    if "link_index" in container_interface and container_interface["link_index"] == ttt[1]:
                        # print(f"found container interface for container {c.name} on bridge br-{network.short_id}")
                        ttt += [c.name]
                        # print(ttt)
                for elem in info_list:
                    # if "link_index" in container_interface:
                    #     print(f"elem is: {elem}; looking for link_index {container_interface['link_index']}")
                    if "link_index" in container_interface and container_interface["link_index"] == elem["ifindex"]:
                        elem["container_name"] = c.name
                        elem["network_name"] = network.name
                        # print(f"********* setting container_name for ifindex {elem['ifindex']} to {c.name}")
                    # else:
                    #     if "link_index" in container_interface:
                    #         print(f"elem link_index {elem['link_index']} not container link index {container_interface['link_index']}")
                        
        # print(t1)
        all_results += [t1]
        
        # print("all_results is:")
        # print(all_results)

        # print("info_list is:")
        # print(json.dumps(info_list, indent=2))

        self.scenario.host_network_info += info_list

        return(all_results)

    #
    # Given the interface mapping, produce a 'short mapping' of the form:
    #
    # {('container2', 'container1'): 'host_veth1', ('container1', 'container2'): 'host_veth2'}
    #
    # Useful because, to delay traffic from container2 to container1, add a netem qdisc to host_veth1
    #

    def short_mapping(self, interface_mapping):
        things = {}
        for elem in interface_mapping:
            # print(elem)
            # print("----")
            key = (elem[0][2], elem[1][2])
            things[key] = elem[0][0]
            key = (elem[1][2], elem[0][2])
            things[key] = elem[1][0]
        return(things)


    def build_full_shortmap(self, network_list):
        ret = {}
        self.host_network_info = []
        print(f"in build_full_shortmap network_list is: {network_list}")

        for net_name in network_list:
            # print(f"Building interface mapping for {net_name}")
            tmp = self.build_interface_mapping(network_list[net_name])
            self.host_network_info += [tmp]
            tmp2 = self.short_mapping(tmp)
            ret.update(tmp2)

        # print("##### Host Network Info ########")
        # print(json.dumps(self.scenario.host_network_info, indent=2))
        # print("#############")

        return(ret)            


    # Return a list of (src, dst) pairs that includes one such
    # pair for each link in the topology database (over all time)
    def list_link_pairs(self):
        # Get unique (src, dst) pairs
        unique_pairs = self.df[["source", "dest"]].drop_duplicates()

		# Convert the result to a list of tuples
        unique_pairs_list = list(map(tuple, unique_pairs.values))
		
        return(unique_pairs_list)

    #
    # Instantiate the virtual networks among nodes
    # (includes all possible connectivity)
    #
    # Install netem on the host virtual interfaces so that packets can be
    # appropriately manipulated (delayed, lost)
    #
    def instantiate_networks(self):

        #
        # Set up defaults for unspecified networks.
        #
        default_num_hosts = 2
        current_ipv4_network = "10.128.0.0"
        if "default" in self.scenario.scenario_dict["networks"]:
            if "IPv4" in self.scenario.scenario_dict["networks"]["default"]:
                if "network" in self.scenario.scenario_dict["networks"]["default"]["IPv4"]:
                    current_ipv4_network = self.scenario.scenario_dict["networks"]["default"]["IPv4"]["network"]
                if "num_hosts" in self.scenario.scenario_dict["networks"]["default"]["IPv4"]:
                    default_num_hosts = self.scenario.scenario_dict["networks"]["default"]["IPv4"]["num_hosts"]

        logger.info(f"List of networks is: {self.scenario.scenario_dict['networks']}")
        for n in self.scenario.scenario_dict["networks"]:
            if n=="defaults":
                continue

            if n in self.scenario.networks:
                logger.info(f"Already have a network named {n}; not making another")
                continue

            logger.info(f"Instantiating network {n} : {self.scenario.scenario_dict['networks'][n]}")

            #
            #
            #
            if "network" not in self.scenario.scenario_dict['networks'][n]:
                #
                # Need to make up a network
                # +3 to account for network, broadcast, and gateway
                if "num_hosts" in self.scenario.scenario_dict['networks'][n]:
                    num_hosts = 3+self.scenario.scenario_dict['networks'][n]["num_hosts"]
                else:
                    num_hosts = 3+default_num_hosts

                if self.scenario.scenario_dict['networks'][n]["IPVersion"]==4:
                    tmp = ipaddress.IPv4Network(current_ipv4_network)
                    prefixlen = int(32-math.log(num_hosts, 2))

                    tmp_net = tmp.supernet(new_prefix=prefixlen)
                    the_network = f"{tmp_net}"
                    the_gateway = f"{tmp_net.broadcast_address-1}"

                    current_ipv4_network = tmp_net.broadcast_address+1
                else:
                    logger.fatal("Can only automatically generate IPv4 networks right now.")
                    sys.exit(-1)
            else:
                # Network is fully specified in the scenario file
                the_network = self.scenario.scenario_dict['networks'][n]["network"]
                the_gateway = self.scenario.scenario_dict['networks'][n]["gateway"]

            net = self.create_network(the_network, the_gateway, n)
            self.scenario.networks[n] = net
        
        #
        # Connect containers to networks
        #
        for n in self.scenario.scenario_dict["node_configs"]:
            if n=="DEFAULT" or n=="__global":
                continue
            
            container = self.scenario.nodes[n].container
            for intf in self.scenario.scenario_dict["node_configs"][n]["ipv4_addresses"]:
                net_name = intf[0]
                if len(intf)>1:
                    address = intf[1]
                else:
                    address = None
                logger.info(f"Connecting container {n} to network {net_name} at address {address}")
                self.scenario.networks[net_name].connect(container, address)

        # Get dynamic information from containers (interface names, MAC addresses, ...)
        for c in self.scenario.nodes:
            the_c = self.scenario.nodes[c].container
            out = the_c.exec_run("ip --json addr show")
            output = out.output.decode("utf-8")
            info = json.loads(output)
            self.scenario.container_info[the_c.name] = info

        # Install netem on all networks (on the host sides of the interfaces)

        self.iface_info = self.build_full_shortmap(self.scenario.networks)
        logger.info(f"Host interface info:\n{self.iface_info}")

        for elem in self.iface_info:
            logger.info(f"Adding netem to {self.iface_info[elem]}")
            out = subprocess.run(f"tc qdisc add dev {self.iface_info[elem]} root netem delay 0ms".split(), capture_output=True)
            data = out.stdout.decode("utf-8")
            logger.info(f"adding netem to {self.iface_info[elem]} gives {data}")

        #
        #
        #
        with open(f"{self.scenario.scenario_dir}/mounts/global/scenario_info.json", "w") as fp:
            fp.write(json.dumps(self.scenario.host_network_info, indent=2))
        
        # Augment the container dynamic info with docker network names
        logger.info("Augmenting container network info with docker network names.")
        for c in self.scenario.container_info:
            the_c = self.scenario.container_info[c]
            for intf in the_c:
                for d in self.scenario.host_network_info:
                    # print(f"d is {d}")
                    # print(f"############################## the_c {intf['ifindex']}  d {d['link_index']}")
                    if (intf["ifindex"]==d["link_index"]) and (c==d['container_name']):
                        intf["network_name"] = d["network_name"]


if __name__=="__main__":
    logger.info("Can't test netem_topology directly.")
