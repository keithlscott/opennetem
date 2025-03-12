#!/usr/bin/env python3

import sys
import os
import json
import ipaddress

#
# This file provides a set of functions for getting information about
# the running (network) state of an opennetem emulation.
#

#
# Containerinfo.json is a dictionary indexed by opennetem node name
# where they values are lists of dictionaries where each dictionary
# contains information about one of the node's interfaces.  The
# interface infor is 'augmented' w.r.t. the base info with the name
# of the opennetem network to which the interface is connected
# (if it is indeed connected to an opennetem network).
#
# {
#   "node_a": [
#     {
#       "ifindex": 1,
#       "ifname": "lo",
#       "flags": [
#         "LOOPBACK",
#         "UP",
#         "LOWER_UP"
#       ],
#       "mtu": 65536,
#       "qdisc": "noqueue",
#       "operstate": "UNKNOWN",
#       "group": "default",
#       "txqlen": 1000,
#       "link_type": "loopback",
#       "address": "00:00:00:00:00:00",
#       "broadcast": "00:00:00:00:00:00",
#       "addr_info": [
#         {
#           "family": "inet",
#           "local": "127.0.0.1",
#           "prefixlen": 8,
#           "scope": "host",
#           "label": "lo",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         },
#         {
#           "family": "inet6",
#           "local": "::1",
#           "prefixlen": 128,
#           "scope": "host",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         }
#       ]
#     },
#     {
#       "ifindex": 2,
#       "link_index": 2051,
#       "ifname": "dock",
#       "flags": [
#         "BROADCAST",
#         "MULTICAST",
#         "UP",
#         "LOWER_UP"
#       ],
#       "mtu": 1500,
#       "qdisc": "noqueue",
#       "operstate": "UP",
#       "group": "default",
#       "link_type": "ether",
#       "address": "72:e2:c2:82:98:aa",
#       "broadcast": "ff:ff:ff:ff:ff:ff",
#       "link_netnsid": 0,
#       "addr_info": [
#         {
#           "family": "inet",
#           "local": "172.17.0.3",
#           "prefixlen": 16,
#           "broadcast": "172.17.255.255",
#           "scope": "global",
#           "label": "dock",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         }
#       ]
#     },
#     {
#       "ifindex": 3,
#       "link_index": 2054,
#       "ifname": "mon",
#       "flags": [
#         "BROADCAST",
#         "MULTICAST",
#         "UP",
#         "LOWER_UP"
#       ],
#       "mtu": 1500,
#       "qdisc": "noqueue",
#       "operstate": "UP",
#       "group": "default",
#       "link_type": "ether",
#       "address": "d6:b2:44:fe:50:30",
#       "broadcast": "ff:ff:ff:ff:ff:ff",
#       "link_netnsid": 0,
#       "addr_info": [
#         {
#           "family": "inet",
#           "local": "172.19.0.8",
#           "prefixlen": 16,
#           "broadcast": "172.19.255.255",
#           "scope": "global",
#           "label": "mon",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         }
#       ]
#     },
#     {
#       "ifindex": 4,
#       "link_index": 2060,
#       "ifname": "eth2",
#       "flags": [
#         "BROADCAST",
#         "MULTICAST",
#         "UP",
#         "LOWER_UP"
#       ],
#       "mtu": 1500,
#       "qdisc": "noqueue",
#       "operstate": "UP",
#       "group": "default",
#       "link_type": "ether",
#       "address": "c6:51:cd:61:ed:35",
#       "broadcast": "ff:ff:ff:ff:ff:ff",
#       "link_netnsid": 0,
#       "addr_info": [
#         {
#           "family": "inet",
#           "local": "10.44.3.1",
#           "prefixlen": 24,
#           "broadcast": "10.44.3.255",
#           "scope": "global",
#           "label": "eth2",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         }
#       ],
#       "network_name": "ab"
#     },
#     {
#       "ifindex": 5,
#       "link_index": 2061,
#       "ifname": "eth3",
#       "flags": [
#         "BROADCAST",
#         "MULTICAST",
#         "UP",
#         "LOWER_UP"
#       ],
#       "mtu": 1500,
#       "qdisc": "noqueue",
#       "operstate": "UP",
#       "group": "default",
#       "link_type": "ether",
#       "address": "2e:c9:b1:2a:0c:48",
#       "broadcast": "ff:ff:ff:ff:ff:ff",
#       "link_netnsid": 0,
#       "addr_info": [
#         {
#           "family": "inet",
#           "local": "10.46.7.1",
#           "prefixlen": 24,
#           "broadcast": "10.46.7.255",
#           "scope": "global",
#           "label": "eth3",
#           "valid_life_time": 4294967295,
#           "preferred_life_time": 4294967295
#         }
#       ],
#       "network_name": "ac"
#     }
#   ],


class opennetem_runtime(object):
    def __init__(self, globals_dir=None):
        if globals_dir==None:
            self.globals_dir = "/var/run/opennetem/"
            print(f"Setting self.globals_dir to {self.globals_dir}")

        try:
            with open(f"{self.globals_dir}/container_info.json") as cifp:
                data = cifp.read()
                self.container_info = json.loads(data)

            with open(f"{self.globals_dir}/scenario.json") as sfp:
                data = sfp.read()
                self.scenario = json.loads(data)

        except Exception as e:
            print(f"Can't open one of [scenario.json, container_info.json] from {self.globals_dir}")
            sys.exit(-1)

        pidfile = f"{self.globals_dir}/pid"
        if os.path.exists(pidfile):
            with open(f"{self.globals_dir}/pid", "r") as pfp:
                data = pfp.read()
                self.pid = int(data)
        else:
            self.pid = -1

        return


    def list_nodes(self):
        return list(self.container_info.keys())


    def node_from_ip(self, ip_string):
        for node in self.list_nodes():
            for interface in self.container_info[node]:
                for info in interface["addr_info"]:
                    if info["local"]==ip_string:
                        return(node)
        return None

    #
    # Return a list of node names
    #
    def nodes_on_network(self, target_network):
        ret = []
        for node in self.list_nodes():
            for interface in self.container_info[node]:
                for ifaddrinfo in interface["addr_info"]:
                    if ipaddress.IPv4Address(ifaddrinfo['local']) in target_network:
                        ret += [node]
        return(ret)
    

    #
    # Return the opennetem network name for a given address.
    #
    def network_name_from_address(self, ip_address_string):
        for node in self.list_nodes():
            for interface in self.container_info[node]:
                for ifaddrinfo in interface["addr_info"]:
                    if ifaddrinfo["family"] != "inet":
                        continue
                    if ifaddrinfo['local']  == str(ip_address_string):
                        # print(json.dumps(ifaddrinfo, indent=2))
                        if "network_name" in interface:
                            return(interface["network_name"])
        return(None)
    

    # Return a list of IPv4Addresses on the network
    def addrs_on_network(self, target_network):
        ret = []
        for node in self.list_nodes():
            for interface in self.container_info[node]:
                for ifaddrinfo in interface["addr_info"]:
                    if ifaddrinfo['family']!="inet":
                        continue
                    # print(interface['addr_info'])
                    if ipaddress.IPv4Address(ifaddrinfo['local']) in target_network:
                        ret += [ipaddress.IPv4Address(ifaddrinfo['local'])]
        return(ret)

    # return a list of ipv4address.ipv4network instances for the node
    def get_opennetem_networks(self, node):
        exclude_interfaces = ["lo", "mon", "dock"]
        res = []

        for interface in self.container_info[node]:
            if interface["ifname"] in exclude_interfaces:
                continue

            for info in interface["addr_info"]:
                if info["family"]!="inet":
                    continue

                res += [ipaddress.IPv4Network(f"{info['local']}/{info['prefixlen']}", strict=False)]

        return res


if __name__=="__main__":
    foo = opennetem_runtime()
    print(f"nodes are {foo.list_nodes()}")
    for addr in ["10.44.3.1", "10.44.3.2", "10.45.7.1", "10.45.7.2", "10.45.7.5"]:
        print(f"node_from_ip({addr}) is {foo.node_from_ip(addr)}")

    for node in foo.list_nodes():
        print(f"{node} networks")
        res = foo.get_opennetem_networks(node)
        print(res)


