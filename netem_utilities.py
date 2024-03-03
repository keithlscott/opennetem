#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import os
import sys
import pwd
import json
import docker
import multiprocessing
import time
import logging
import netem_logging
import clean_containers
import socket

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logger = netem_logging.get_sublogger("utilities")

client = docker.from_env()

class influxdb_support(object):
    def __init__(self):
        # token = os.environ.get("INFLUXDB_TOKEN")
        self.token = "9Q3OsSe5OFZBb0EWUVzcmERy80ZPI8yHORRs14dXGQmoZ0ySOGcShf3vlbZWlAebN3X_2vvO3wy_lQmWL7M71A=="
        self.org = "netem"
        #self.url = "http://influxdb2:8086"
        self.url = "http://localhost:8086"

        self.client = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            
    def write_value(self, measurement_name, measurement_val, tags_dict = {}, other_fields_dict = {}):
        try:
            fields_dict = {"value": measurement_val}
            fields_dict.update(other_fields_dict)
            dictionary = {
                "measurement": measurement_name,
                "tags": tags_dict,
                "fields": fields_dict,
            }
            logger.info(f"Logging dict to influxdb: {dictionary}")
            ret = self.write_api.write(bucket="netem", org="netem", record=dictionary)
        except Exception as e:
            logger.warning(f"Error writing to influxdb: {e}")

    def write_point(self, point):
         logger.info(f"Logging point to influxdb: {point}")
         self.write_api.write(bucket="netem", org="netem", record=point)


def apply_to_all_containers(func):
    logger.info(f"In apply_to_all_containers {func.__name__}")
    # containers = client.containers.list(all=True, filters={"name": "netem*"})
    containers = client.containers.list(all=True, filters={"label": ["netem_node=True"]})

    with multiprocessing.Pool(processes=3) as pool:
        container_names = [x.name for x in containers]
        cremove_result = pool.map_async(func=func,
                                        iterable=container_names)
        pool.close()
        # pool.terminate()
        pool.join()
        
    while not cremove_result.ready():
        logger.info("operation on containers not done yet")
        time.sleep(5)
    logger.info(f"Done with apply_to_all_containers {func.__name__}")


def robustly_read_json_file(filename):
    while True:
        try:
            with open(filename, "r") as fp:
                data = fp.read()
                info = json.loads(data)
                return(info)
        except Exception as e:
            time.sleep(5)


def glippy(container_name, command):
    container = client.containers.list(all=True, filters={"name": container_name})
    ret = container.exec_run(command)
    return ret


def run_command_in_all_containers(command):
    apply_to_all_containers(lambda x: glippy(x, command))


def remove_all_networks():
    # networks = client.networks.list(names="netem*")
    networks = client.networks.list(filters={"label": ["netem_network=True"]})
    print([x.name for x in networks])
    for n in networks:
        n.remove()


def check_running():
    containers = client.containers.list(all=True, filters={"label": ["netem_node=True"]})
    networks = client.networks.list(filters={"label": ["netem_network=True"]})

    if len(containers)>0 or len(networks)>0:
        print(f"It seems like there are existing containers and/or networks.")
        print("Remove them or Cancel?  (R/c)")
        res = str(input())
        if len(res)==0 or res[0]=="R" or res[0]=="r" or res[0]=="Y" or res[0]=="y":
            logger.info("Removing existing infrastructure.")
            clean_containers.cleanup_all()
        else:
            logger.info("Canceling due to existing infrastructure.")
            sys.exit(0)


def change_ownership_and_group(directory, new_owner, new_group):
    # Get the user ID of root
    root_uid = pwd.getpwnam('root').pw_uid
    
    # Change ownership and group of files and directories recursively
    for root, dirs, files in os.walk(directory):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            if os.stat(dir_path).st_uid == root_uid:
                os.chown(dir_path, new_owner, new_group)
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if os.stat(file_path).st_uid == root_uid:
                os.chown(file_path, new_owner, new_group)


def reset_ownership(directory):
    the_user = int(os.getenv("SUDO_UID"))
    the_group = int(os.getenv("SUDO_GID"))
    logger.info(f"Resetting ownership to {the_user}:{the_group}")
    change_ownership_and_group(directory, the_user, the_group)


def get_reltime(host="monitor-netem_utilities-1", port=8088, new_start=None):
    # Create a TCP socket
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the server
        tcp_socket.connect((host, port))
        print("Connected to", host, "on port", port)
        print(f"new_start is: {new_start}")

        to_send = b''
        # Send an empty packet
        if new_start==None:
            pass
        elif new_start==-1:
            print(f"Sending set to current time: {to_send}")
            to_send = f"set {str(new_start)}".encode("utf-8")
        else:
            print(f"Sending set to specific time: {to_send}")
            to_send = f"set {str(int(time.time()))}".encode("utf-8")
        tcp_socket.sendall(to_send)

        tcp_socket.shutdown(socket.SHUT_WR)
        print("Empty TCP packet sent successfully.")

        # Receive response
        response = tcp_socket.recv(1024)  # Adjust buffer size accordingly
        value=response.decode()
        tcp_socket.close()
        print("Response received:", value)

    except Exception as e:
        print("Error while sending/receiving TCP packet:", e)
    finally:
        # Close the socket
        tcp_socket.close()

#if __name__ == "__main__":
    ## Set the destination host and port
    #destination_host = 'localhost'
    #destination_port = 9080
#
    #parser = argparse.ArgumentParser()
    #parser.add_argument("--set", type=int, default=None)
    #args = parser.parse_args()
#
    ## Send an empty UDP datagram to the specified destination
    #send_and_receive_tcp_packet(destination_host, destination_port, args.set)


# # Get the interface info of the given node's # interfaces to the given network.
#
# network is a netem network name (e.g. "ab")
# Returns tuple of the form: [('eth2', ['10.128.0.1'], '02:42:0a:80:00:01')]
#
def get_interface_info(scenario, node, network, verbose=False):

    if scenario==None:
        with open("/netem/globals/container_info.json", "r") as fp:
            data = fp.read()
            info = json.loads(data)
    else:
        info = scenario.container_info

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
            if interface["network_name"] == network:
                if verbose:
                    print(f"Found netem_{network} in interface")
                    print(interface)
                addrs = []
                for ipaddr in interface["addr_info"]:
                    addrs += [ipaddr["local"]]
                answers += [(interface["ifname"], addrs, interface["address"])]

    return(answers)

def get_ip_addr(scenario, node, network, verbose=False):
    ret = get_interface_info(scenario, node, network, verbose)
    logger.info(f"get_interface_info({node}, {network}) is: {ret}")
    if len(ret[0][1])>=1:
        return ret[0][1][0]
    

    