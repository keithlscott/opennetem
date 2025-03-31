#!/usr/bin/env python3

import json
import ipaddress


class opennetem_runtime(object):
    def __init__(self, globals_dir=None):
        if globals_dir==None:
            self.globals_dir = "./netem/globals"

        with open(f"{self.globals_dir}/container_info.json") as cifp:
            data = cifp.read()
            self.container_info = json.loads(data)

        with open(f"{self.globals_dir}/scenario.json") as sfp:
            data = sfp.read()
            self.scenario = json.loads(data)

        return

    def list_nodes(self):
        return list(self.container_info.keys())
        return

    def node_from_ip(self, ip_string):
        for node in self.list_nodes():
            for interface in self.container_info[node]:
                for info in interface["addr_info"]:
                    if info["local"]==ip_string:
                        return(node)
        return None


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


