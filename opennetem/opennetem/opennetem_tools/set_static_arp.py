#!/usr/bin/env python3

import argparse
import json
import subprocess

#
# Get the mac addresses of the given node's
# interfaces to the given network.
#
# network is a netem network name (e.g. "ab")
#
def get_mac_addresses(node, network, verbose, container_info=None):
    if container_info==None:
        with open("/netem/globals/container_info.json", "r") as fp:
            data = fp.read()
            info = json.loads(data)
    else:
        info = container_info
        
    if verbose:
        print(json.dumps(info, indent=2))

    answers = []
    ignored_interfaces = ["lo", "dock", "mon"]
    if verbose:
        print(f"Looking for {node} in container_info")
    for search_node in info:
        #if search_node != "netem_"+node:
        if search_node != node:
            if verbose:
                print(f"  Skipping {node} {search_node}")
            continue

        if verbose:
            print(f"Found {search_node} in container_info")
            print(f"Looking for network netem_{network}")
        for interface in info[search_node]:
            if interface["ifname"] in ignored_interfaces:
                continue
            # if interface["network_name"] == "netem_"+network:
            if interface["network_name"] == +network:
                if verbose:
                    print(f"Found netem_{network} in interface")
                    print(interface)
                addrs = []
                for ipaddr in interface["addr_info"]:
                    addrs += [ipaddr["local"]]
                answers += [(interface["ifname"], addrs, interface["address"])]

    return(answers)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node")
    parser.add_argument("--network")
    parser.add_argument("--verbose", action="store_true", default=False)
    args = parser.parse_args()
    print(f"args are: {args}")

    ret = get_mac_addresses(args.node, args.network, args.verbose)
    print(ret)
    for a in ret:
        for ip_addr in a[1]:
            cmd = f"arp -s {ip_addr} {a[2]}"
            ret = subprocess.run(cmd.split(), capture_output=True)
            if args.verbose:
                print(f"Result of {cmd}:")
                print(f"result code: {ret.returncode}")
                print(ret.stdout.decode("utf-8"))


if __name__=="__main__":
    main()

