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

import influxdb_client_3, os, time
from influxdb_client_3 import InfluxDBClient3, Point, WritePrecision
# from influxdb_client_3.client.write_api import SYNCHRONOUS


class influxdb_writer(object):
    def __init__(self):
        # token = os.environ.get("INFLUXDB_TOKEN")
        self.token = "9Q3OsSe5OFZBb0EWUVzcmERy80ZPI8yHORRs14dXGQmoZ0ySOGcShf3vlbZWlAebN3X_2vvO3wy_lQmWL7M71A=="
        self.org = "netem"
        # self.url = "http://monitor-influxdb-1:8086"
        self.url = "http://localhost:8086"

        self.client = influxdb_client_3.InfluxDBClient3(host=self.url,
                                                        token=self.token,
                                                        org=self.org,
                                                        database="netem")

        # self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
    

    def write_value(self, ping_table_data):
        all_ret = []

        # print(f"Writing result value: {ping_table_data}")
        for res in ping_table_data:
            dictionary = {"measurement": "latency_table",
                          "time": res["start_time"],
                          "tags": {"send_time":     res["start_time"],
                                   "source_name":   res["source"],
                                   "dest_name":     res["destination_name"],
                                   "forward":       res["source"] < res["destination_name"],
                                   "network_name":  f"{res['source']}__{res['destination_name']}",
                                   "network_name2": res['network_name']
                                  },
                          "fields": {"value": float(res["rtt_avg"])},
                         }
            # print(f"One write dictionary is: {dictionary}")
            try:
                # ret = self.client.write(bucket="netem", org="netem", record=dictionary)
                ret = self.client.write(record=dictionary)
                all_ret += [ret]
            except Exception as e:
                # print(f"influxdb write error: {e}")
                all_ret += [None]
        return (all_ret)
    

def bundles_queued(docker_client, rtinfo):
    futures = []
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # want time in this format 2021-08-09T18:04:56.865943 for influxdb
        tmp_time = datetime.datetime.now(datetime.timezone.utc)
        #tmp_time = tmp_time - datetime.timedelta(hours=1)
        the_start_time = tmp_time.isoformat()
        for node_name in rtinfo.list_nodes():
                container = docker_client.containers.get(node_name)

                futures.append({"node_name": node_name,
                                        "start_time": the_start_time,
                                        "exec.submit": executor.submit(container.exec_run,
                                                                cmd=f"bplist")})

    # print(futures[0])
    for future in concurrent.futures.as_completed(x["exec.submit"] for x in futures):
        if future.result().exit_code==0:
            the_source = [x["node_name"] for x in futures if x["exec.submit"]==future][0]
            start_time = [x["start_time"] for x in futures if x["exec.submit"]==future][0]
            # print(f"{the_source} {future.result()}")
            # print(f"the_dict is : {the_dict}")
            tmp = future.result().output
            tmp_int = int(tmp)
            the_dict = {"foo": tmp_int,
                        "start_time": str(start_time),
                        "node": the_source}
            
            results += [the_dict]

    return(results)


if __name__=="__main__":
    do_main()

def do_main():
    client = docker.from_env()

    rtinfo = opennetem_runtime.opennetem_runtime()

    foo = influxdb_writer()

    # results = ping_search3(client, rtinfo)
    # print(json.dumps(results, indent=2))

    print("Now doing multiple results")
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
        measurement_interval = 1
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
                    futures.append(executor.submit(bundles_queued, client, rtinfo))
                except Exception as e:
                    print(f"submit error: {e}")
                    sys.exit(0)

                next_time += measurement_interval

            if last_futures_len != len(futures):
                last_futures_len = len(futures)
                # print("resetting timeouts 1")
                timeouts = 0

            to_remove = []
            try:
                # print(f"Looking for available futures; len(futures) is {len(futures)}.")

                if len(futures)==0:
                    time.sleep(1)
                    raise(concurrent.futures._base.TimeoutError())
                
                for future in concurrent.futures.as_completed(futures, timeout=1):
                    print(f"A future became available from {len(futures)} futures; future has {len(future.result())} results.")
                    # print(future.results())
                    # print("resetting timeouts 2")
                    timeouts = 0
                    # print(f"+++++ {json.dumps(future.result(), indent=2)}")

                    # The res is a list of dictionaries of the following form that includes
                    # information for all source nodes about all their immediate neighbors.
                    #
                    # [ { "start_time": ,
                    #     "source": ,
                    #     "destination_name":
                    #     "rtt_avg"
                    #   },
                    #   ...
                    # ]

                    all_ret = foo.write_value(future.result())
                    print(f"return from ifluxdb write: {all_ret}")

                    to_remove += [future]

                for f in to_remove:
                    futures.remove(f)
                to_remove = []

            except concurrent.futures._base.TimeoutError as e:
                print(f"Futures timeout: {e}")
                timeouts += 1
                next_time = time.time() + measurement_interval

            except docker.errors.NotFound or docker.errors.APIError as e:
                print(f"Docker container not found: {e.args}")
                time.sleep(5)
                client = docker.from_env()
                rtinfo = opennetem_runtime.opennetem_runtime()
                futures = []
                timeouts += 1
                next_time = time.time() +measurement_interval

            except Exception as e:
                print(f"Unhandled exception {e} of type {type(e)}")
                sys.exit(-1)

            sleep_diff = next_time-time.time()
            to_sleep = max(0, sleep_diff)
            time.sleep(to_sleep)

    print("############")
