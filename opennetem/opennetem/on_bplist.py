#! /usr/bin/env python3

import sys
import docker
import json
import ipaddress
from pythonping import ping
import concurrent.futures
import pingparsing
import opennetem.runtime as opennetem_runtime
import ipaddress
import datetime
import time
from itertools import groupby, chain

import influxdb_client, os, time
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS


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


def parse_bplist(bplist):
    ret = []
    translation_table = dict.fromkeys(map(ord, "'"), None)
    
    for rec in get_sections(bplist):
        the_dict = {}
        for l in rec: # for each line
            toks = l.split()
            for item in ["Source EID", "Destination EID", "Report-to EID"]:
                if l.find(item)>=0:
                    the_dict[item] = toks[-1].translate(translation_table)
        if the_dict != {}:
            ret += [the_dict]

    # print("returning from parse_bplist")
    # print(ret)
    return(ret)

all_ever = {} #{at_node: [(source_node, dest_node)]}

#
# Do one round of bplists, one per node
#
def bplist(docker_client, rtinfo):
    global all_ever
    futures = []
    results = []
    done_this_time = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # want time in this format 2021-08-09T18:04:56.865943 for influxdb
        tmp_time = datetime.datetime.now(datetime.timezone.utc)
        #tmp_time = tmp_time - datetime.timedelta(hours=1)
        the_start_time = tmp_time.isoformat()
        for node_name in rtinfo.list_nodes():
                container = docker_client.containers.get(node_name)

                # """/bin/bash -c '{tmp["command"]}'"""
                #cmd = "tail -9 ION_CONFIGS/ion.log"
                cmd = "bplist"
                futures.append({"node_name": node_name,
                                "start_time": the_start_time,
                                "exec.submit": executor.submit(container.exec_run, cmd=cmd)})

    for future in concurrent.futures.as_completed(x["exec.submit"] for x in futures):
        if future.result().exit_code==0:
            the_source = [x["node_name"] for x in futures if x["exec.submit"]==future][0]
            start_time = [x["start_time"] for x in futures if x["exec.submit"]==future][0]
            # print(f"{the_source} {future.result()}")
            # print(f"the_dict is : {the_dict}")
            tmp = future.result().output.decode("utf-8")

            if False:
                with open("foo.txt", "r") as fp:
                    tmp = fp.read()
            
            dict_list = parse_bplist(tmp)
            # [{'Source EID': 'ipn:5.2', 'Destination EID': 'ipn:1.1', 'Report-to EID': 'ipn:5.2'},
            #  {'Source EID': 'ipn:5.2', 'Destination EID': 'ipn:1.1', 'Report-to EID': 'ipn:5.2'},
            #  o o o
            #  {'Source EID': 'ipn:5.2', 'Destination EID': 'ipn:1.1', 'Report-to EID': 'ipn:5.2'},
            #  {'Source EID': 'ipn:5.2', 'Destination EID': 'ipn:1.1', 'Report-to EID': 'ipn:5.2'}]

            tmp = {}
            for elem in dict_list:
                if elem["Source EID"] not in tmp:
                        tmp[elem["Source EID"]] = {}
                if elem["Destination EID"] not in tmp[elem["Source EID"]]:
                        tmp[elem["Source EID"]][elem["Destination EID"]] = 0
                tmp[elem["Source EID"]][elem["Destination EID"]] += 1

            # so now tmp[x][y] is the number of bundles in queue with src eid x
            # and dest eid y
            if (len(tmp)>0):
                for from_eid in tmp:
                     toks = from_eid.split(":")
                     toks2 = toks[1].split(".")
                     from_node_number = int(toks2[0])
                     from_service_number = int(toks2[1])
                     for to_eid in tmp[from_eid]:
                        toks3 = to_eid.split(":")
                        toks4 = toks3[1].split(".")
                        to_node_number = int(toks4[0])
                        to_service_number = int(toks4[1])
                        tmp2 = {"measurement": "bplist",
                                "fields": {"value": tmp[from_eid][to_eid]},
                                "tags": {"node": the_source,
                                         "src_node": from_node_number,
                                         "src_service": from_service_number,
                                         "dst_node": to_node_number,
                                         "dst_service": to_service_number}
                                }
                        results += [tmp2]

                        if the_source not in done_this_time:
                             done_this_time[the_source] = []
                        if ((from_node_number, to_node_number)) not in done_this_time[the_source]:
                             done_this_time[the_source] += [(from_node_number, to_node_number)]

    # Now for all n:(s,d) elements in all_ever that we did NOT do this time, enter zero
    # print("Now looking to zero out stuff")
    # print(f"all_ever is: {all_ever}")
    # print(f"done_this_time is: {done_this_time}")

    for at_node in done_this_time:
        if at_node not in all_ever:
              all_ever[at_node] = []
        for elem in done_this_time[at_node]:
            if elem not in all_ever[at_node]:
                 all_ever[at_node] += [elem]

    for at_node in all_ever:
        need_zeros = all_ever[at_node].copy()

        if at_node in done_this_time:
            for the_pair in done_this_time[at_node]:
                if the_pair in all_ever[at_node]:
                    need_zeros.remove(the_pair)
                    continue
                all_ever[at_node] += [the_pair]

        for elem in need_zeros:
            tmp2 = {"measurement": "bplist",
                    "fields": {"value": 0},
                    "tags": {"node": at_node,
                                "src_node": elem[0],
                                "src_service": -1,
                                "dst_node": elem[1],
                                "dst_service": -1}
                    }
        results += [tmp2]

    return(results)

     
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

            foo.write_value([{"measurement": "ion_node_numbers",
                            "fields": {"value": node_num}}])
        except:
             pass
        
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        result_matrices = {}
        count = 0
        next_time = time.time()
        timeouts = 0
        max_timeouts = 3
        last_futures_len = 0
        max_measurements = 0
        num_measurements = 0
        measurement_interval = 5
        done = False

        while not done:
            if timeouts>=max_timeouts:
                done = True
                continue

            # print(f"time: {time.time()}  next_time: {next_time}  timeouts: {timeouts}")
            if time.time()>=next_time and (max_measurements<=0 or num_measurements<max_measurements):
                num_measurements += 1
                # print(f"taking measurement at time {datetime.datetime.now()}")
                try:
                    futures.append(executor.submit(bplist, client, rtinfo))
                except Exception as e:
                    print(f"submit error: {e}")
                    sys.exit(0)

                next_time += measurement_interval

            if last_futures_len != len(futures):
                last_futures_len = len(futures)
                timeouts = 0

            to_remove = []
            try:
                # print(f"Looking for available futures; len(futures) is {len(futures)}.")

                if len(futures)==0:
                    time.sleep(1)
                    raise(concurrent.futures._base.TimeoutError())
                
                for future in concurrent.futures.as_completed(futures, timeout=1):
                    # print(f"A future became available from {len(futures)} futures; future has {len(future.result())} results.")
                    # print(future.result())
                    # print("resetting timeouts 2")
                    timeouts = 0

                    all_ret = foo.write_value(future.result())

                    to_remove += [future]

                for f in to_remove:
                    futures.remove(f)
                to_remove = []

            except concurrent.futures._base.TimeoutError as e:
                # print(f"Futures timeout: {e}")
                timeouts += 1
                next_time = time.time() + measurement_interval

            except docker.errors.NotFound or docker.errors.APIError as e:
                # print(f"Docker container not found: {e.args}")
                time.sleep(5)
                client = docker.from_env()
                rtinfo = opennetem_runtime.opennetem_runtime()
                futures = []
                timeouts += 1
                next_time = time.time() + measurement_interval

            except Exception as e:
                print(f"Unhandled exception {e} of type {type(e)}")
                sys.exit(-1)

            sleep_diff = next_time-time.time()
            to_sleep = max(0, sleep_diff)
            time.sleep(to_sleep)

    # print("############")


if __name__=="__main__":
    do_main()

