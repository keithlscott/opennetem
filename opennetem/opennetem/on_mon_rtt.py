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
import opennetem.utilities as utilities
import logging

def ping_search3(docker_client, rtinfo):

    futures = []
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # want time in this format 2021-08-09T18:04:56.865943 for influxdb
        tmp_time = datetime.datetime.now(datetime.timezone.utc)
        #tmp_time = tmp_time - datetime.timedelta(hours=1)
        the_start_time = tmp_time.isoformat()
        for node_name in rtinfo.list_nodes():
            container = docker_client.containers.get(node_name)
            opennetem_networks = rtinfo.get_opennetem_networks(node_name) # List if IPv4Network instances

            for ipv4Network in opennetem_networks:
                addrs_on_network = rtinfo.addrs_on_network(ipv4Network)

                for addr in addrs_on_network:
                    if rtinfo.node_from_ip(str(addr))==node_name:
                        continue
                    if addr in ipv4Network:
                        futures.append({"node_name": node_name,
                                         "start_time": the_start_time,
                                         "exec.submit": executor.submit(container.exec_run,
                                                                        cmd=f"ping -c 3 -i 0 {str(addr)}")})

    parser = pingparsing.PingParsing()
    # print(futures[0])
    for future in concurrent.futures.as_completed(x["exec.submit"] for x in futures):
        if future.result().exit_code==0:
            the_source = [x["node_name"] for x in futures if x["exec.submit"]==future][0]
            start_time = [x["start_time"] for x in futures if x["exec.submit"]==future][0]
            # print(f"{the_source} {future.result()}")
            stats = parser.parse(future.result().output)
            the_dict = stats.as_dict()
            # print(f"the_dict is : {the_dict}")
            the_dict["source"] = the_source
            the_dict["start_time"] = str(start_time)
            the_dict["destination_name"] = rtinfo.node_from_ip(the_dict["destination"])
            the_dict["network_name"] = rtinfo.network_name_from_address(ipaddress.ip_address(the_dict["destination"]))
            # print(f"the network name is {the_dict['network_name']}")
            # print(json.dumps(the_dict, indent=2))
            # print(stats)
            if the_dict["destination_name"] != None:
                # print(f"adding results for ping from {the_dict['source']} to {the_dict['destination_name']}")
                results += [the_dict]

    return(results)


def do_main(scenario_dir=None):
    client = docker.from_env()
    print("About to do_logging_config")
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler("on_mon_rtt.log"),
                              logging.StreamHandler()])
    
    mylogger = logging.getLogger("monrtt")
    mylogger.info("initialized monrtt logger")

    rtinfo = opennetem_runtime.opennetem_runtime()

    influxdb_support = utilities.influxdb_support()

    # mylogger.info("Now doing multiple results")
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
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

            mylogger.info("top of while loop")
            # print(f"time: {time.time()}  next_time: {next_time}  timeouts: {timeouts}")
            if time.time()>=next_time and (max_measurements<=0 or num_measurements<max_measurements):
                num_measurements += 1
                # print(f"taking measurement at time {datetime.datetime.now()}")
                try:
                    futures.append(executor.submit(ping_search3, client, rtinfo))
                except Exception as e:
                    print(f"submit error: {e}")
                    sys.exit(0)

                next_time += measurement_interval

            if last_futures_len != len(futures):
                last_futures_len = len(futures)
                # print(f"on_mon_rtt: resetting timeouts from {timeouts} to 0 location 1")
                timeouts = 0

            to_remove = []
            try:
                # print(f"Looking for available futures; len(futures) is {len(futures)}.")

                if len(futures)==0:
                    time.sleep(1)
                    raise(concurrent.futures._base.TimeoutError())
                
                to_remove = []

                for future in concurrent.futures.as_completed(futures, timeout=1):
                    # print(f"A future became available from {len(futures)} futures; future has {len(future.result())} results.")
                    # print(future.results())

                    # This will re-raise any exceptions from the call
                    future.result()

                    # print(f"on_mon_rtt: resetting timeouts from {timeouts} to 0 location 2")
                    # print(future)
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

                    # WAS THIS all_ret = foo.write_value(future.result())

                    for res in future.result():
                        # dictionary = {"measurement": "latency_table",
                        #   "time": res["start_time"],
                        #   "tags": {"send_time":     res["start_time"],
                        #            "source_name":   res["source"],
                        #            "dest_name":     res["destination_name"],
                        #            "forward":       res["source"] < res["destination_name"],
                        #            "network_name":  f"{res['source']}__{res['destination_name']}",
                        #            "network_name2": res['network_name']
                        #           },
                        #   "fields": {"value": float(res["rtt_avg"])},
                        #  }
                        # print(f"One write dictionary is: {dictionary}")

                        try:
                            # ret = self.client.write(bucket="netem", org="netem", record=dictionary)
                            influxdb_support.write_value("latency_table", float(res["rtt_avg"]),
                                                         tags_dict = {"send_time":     res["start_time"],
                                                                        "source_name":   res["source"],
                                                                        "dest_name":     res["destination_name"],
                                                                        "forward":       res["source"] < res["destination_name"],
                                                                        "network_name":  f"{res['source']}__{res['destination_name']}",
                                                                        "network_name2": res['network_name']},
                                                         other_fields_dict={"time": res["start_time"]})
                        except Exception as e:
                            print(f"influxdb write error: {e}")
                    
                    to_remove += [future]

                for f in to_remove:
                    futures.remove(f)
                to_remove = []

            except concurrent.futures._base.TimeoutError as e:
                timeouts += 1
                print(f"on_mon_rtt: Futures timeout: {e}; timeouts={timeouts}")
                next_time = time.time() + measurement_interval

            except docker.errors.NotFound or docker.errors.APIError as e:
                print(f"on_mon_rtt: Docker container not found: {e.args}; timeouts={timeouts}")
                time.sleep(5)
                client = docker.from_env()
                rtinfo = opennetem_runtime.opennetem_runtime()
                futures = []
                timeouts += 1
                next_time = time.time() +measurement_interval

            except Exception as e:
                print(f"on_mon_rtt: Unhandled exception {e} of type {type(e)}")
                sys.exit(-1)

            sleep_diff = next_time-time.time()
            to_sleep = max(0, sleep_diff)
            time.sleep(to_sleep)

    print("############")


if __name__=="__main__":
    do_main()

