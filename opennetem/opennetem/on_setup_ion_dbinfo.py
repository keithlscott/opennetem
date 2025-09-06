#! /usr/bin/env python3

import sys
import docker
# import json
# import ipaddress
# from pythonping import ping
# import concurrent.futures
# import pingparsing
import opennetem.runtime as opennetem_runtime
# import ipaddress
# import argparse
# import datetime
# import time
# from itertools import groupby, chain
import logging

import influxdb_client, os, time
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/run/opennetem/on_setup_ion_dbinfo.log', encoding='utf-8', level=logging.DEBUG)
logger = logging.getLogger("on_setup_ion_dbinfo")


#
# Split the bplist output into one 'record' (group of lines) per
# bundle
#
def get_sections(bplist_output):
        lines = bplist_output.split("\n")

        grps = groupby(lines, key=lambda x: x.lstrip().startswith("**** Bundle"))
        for k, v in grps:
                if k:
                        yield chain([next(v)], (next(grps)[1]))  # all lines up to next #TYPE


class influxdb_writer(object):
    def __init__(self):
        # token = os.environ.get("INFLUXDB_TOKEN")
        self.token = "9Q3OsSe5OFZBb0EWUVzcmERy80ZPI8yHORRs14dXGQmoZ0ySOGcShf3vlbZWlAebN3X_2vvO3wy_lQmWL7M71A=="
        self.org = "netem"
        # self.url = "http://monitor-influxdb-1:8086"
        self.url = "http://localhost:8086"

        self.client = influxdb_client.InfluxDBClient(url=self.url,
                                                        token=self.token,
                                                        org=self.org,
                                                        database="netem") 
           
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.delete_api = self.client.delete_api()

    def write_value(self, list_of_dicts):
        all_ret = []

        # print(f"Writing result value: {list_of_dicts}")
        for res in list_of_dicts:
            # print(f"One write dictionary is: {dictionary}")
            try:
                # ret = self.client.write(bucket="netem", org="netem", record=dictionary)
                # print(f"writing record {json.dumps(res, indent=2)}")
                ret = self.write_api.write(bucket="netem", org="netem", record=res)
                all_ret += [ret]
            except Exception as e:
                logger.warning(f"influxdb write error: {e}")
                print(f"influxdb write error: {e}")
                all_ret += [None]

        return (all_ret)
    

    def delete(self, fromtime, totime, measurement, bucket, org):
        # print(f"delete called with measurement_name={measurement}")
        the_thing = f'_measurement="{measurement}"'
        try:
            self.delete_api.delete(fromtime, totime, the_thing, bucket, org)
        except Exception as e:
            print("FIXME in on_bplist influxdb support")


def do_main():
    client = docker.from_env()

    rtinfo = opennetem_runtime.opennetem_runtime()

    foo = influxdb_writer()

    # results = ping_search3(client, rtinfo)
    # print(json.dumps(results, indent=2))

    all_ever = {} # {node_name: [{"from": node_num, "to": node_num}, {}, ...]}

    foo.delete('1970-01-01T00:00:00Z', '2050-04-27T00:00:00Z',
                                    measurement="ion_node_numbers", bucket="netem", org="netem")
    
    #
    # Find ION node numbers and jam them into the database.
    #
    logger.info(f"Examining node list: {rtinfo.list_nodes()}")
    for node in rtinfo.list_nodes():
        try:
            container = client.containers.get(node)
            cmd = """/bin/bash -c 'echo "l endpoint" | bpadmin | head -1'"""
            ret = container.exec_run(cmd=cmd)
            # ": ipn:x.y PID"
            tmp=ret.output.decode("utf-8").split(" ")[1]
            tmp2 = tmp.split(":")[1]
            node_num = int(tmp2.split(".")[0])
            # print(f"node_num: {node_num}")

            logger.info(f"Writing ION node number {node_num} to influxdb.")
            foo.write_value([{"measurement": "ion_node_numbers",
                            "fields": {"value": node_num}}])
        except:
             pass
    
    logger.debug("Node Numbers written to influxdb ion_node_numbers")


if __name__=="__main__":
    do_main()

