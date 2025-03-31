#! /usr/bin/python3

import docker
import json
import ipaddress
from pythonping import ping
import concurrent.futures
import pingparsing
import opennetem_runtime
import ipaddress

def ping_one_host(host):
    # print(f"pinging {host}")
    res = ping(host)
    lines = list(res)
    # print(lines)
    # print(f"type of lines[0] is {type(lines[0])}")
    if str(lines[0]).find("Request timed out")>=0:
        rtt = {}
    else:
        rtt = {host, 1.2}
    return(rtt)

def ping_search(ipv4Network):
    the_hosts = list(ipv4Network.hosts())

    with concurrent.futures.ThreadPoolExecutor(max_workers=300) as executor:
        futures = []

        # print("Appending futures...")
        for host in the_hosts:
            futures.append(executor.submit(ping_one_host, host=host.__format__("s")))

        # print("Now printing results...")
        for future in concurrent.futures.as_completed(futures):
            if future.result()!={}:
                print(future.result())

    return


def ping_search2(docker_client, rtinfo, node_name, ipv4Network):
    the_host_addrs = list(ipv4Network.hosts())
    # print(the_host_addrs)

    print(f"ping_search2 for {node_name}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=300) as executor:
        futures = []
        results = []

        container = docker_client.containers.get(node_name)

        # print(f"Appending futures for {node_name}")
        for host in the_host_addrs:
            target_name = rtinfo.node_from_ip(str(host))
            # print(f"target_name for address {host} is {target_name}")
            if (target_name==None):
                continue
            if target_name==node_name:
                print(f"skipping loopback ping for {node_name}")
                continue
            futures.append(executor.submit(container.exec_run,
                cmd=f"ping -c 3 -i 0 {host.__format__('s')}"))

        # print("Now printing results...")
        parser = pingparsing.PingParsing()
        for future in concurrent.futures.as_completed(futures):
            if future.result().exit_code==0:
                # print(f"{container.name} {future.result()}")
                stats = parser.parse(future.result().output)
                the_dict = stats.as_dict()
                the_dict["source"] = container.name
                the_dict["destination_name"] = rtinfo.node_from_ip(the_dict["destination"])
                # print(json.dumps(the_dict, indent=2))
                # print(stats)
                if the_dict["destination_name"] != None:
                    print(f"adding results for ping from {the_dict['source']} to {the_dict['destination_name']}")
                    results += [the_dict]

    return results


if __name__=="__main__":
    client = docker.from_env()

    rtinfo = opennetem_runtime.opennetem_runtime()

    network = ipaddress.ip_network("10.44.3.0/24")

    for node_name in rtinfo.list_nodes():
        opennetem_networks = rtinfo.get_opennetem_networks(node_name) # List if IPv4Network instances

        for network in opennetem_networks:
            results = ping_search2(client, rtinfo, node_name, network)
            print(json.dumps(results, indent=2))


