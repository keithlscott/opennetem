#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import argparse
import statsd
import socket
import random
import subprocess
import json
import time
import datetime

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import netem_reltime

#
# Create a reltime object; this reads the emulation start time
# from the instance_info.json file and prepares to offer up
# relative times when reltime.get_reltime() is called.
#
reltime = netem_reltime.Reltime()

#
# ping a target and log the results to the screen or to influxdb
#
# NOTE: the RTT logged to influxedb is associated with the SEND_TIME
#       of the ping, NOT  the receive time.

class influxdb_writer(object):
    def __init__(self):
        # token = os.environ.get("INFLUXDB_TOKEN")
        self.token = "9Q3OsSe5OFZBb0EWUVzcmERy80ZPI8yHORRs14dXGQmoZ0ySOGcShf3vlbZWlAebN3X_2vvO3wy_lQmWL7M71A=="
        self.org = "netem"
        self.url = "http://monitor-influxdb-1:8086"

        self.client = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
    

    def write_value(self, src, dst, send_time, val, units):
        dictionary = {
            "time": send_time,
            "measurement": "latency",
            "tags": {"src": src, "dst": dst},
            "fields": {"value": float(val), "units": str(units)},
        }
        ret = self.write_api.write(bucket="netem", org="netem", record=dictionary)
        return(ret)
    

    def write_value2(self, send_time, val, units, extra_tags={}):
        dictionary = {
            "time": send_time,
            "measurement": "latency",
            "tags": extra_tags,
            "fields": {"value": float(val), "units": str(units)},
        }
        ret = self.write_api.write(bucket="netem", org="netem", record=dictionary)
        return(ret)
    
# kscott@nucbuntu:~/Projects/netem/Test$ ./latency_monitor.py
# PING www.google.com(mad41s04-in-x04.1e100.net (2a00:1450:4003:800::2004)) 56 data bytes
# 64 bytes from mad41s04-in-x04.1e100.net (2a00:1450:4003:800::2004): icmp_seq=1 ttl=118 time=7.61 ms

def output_to_dict(ping_output, payload_size, receive_time_str, receive_time_epoch):
    global reltime

    #print(f"in output_to_json: {ping_output} -- {receive_time_str}")
    ret_dict = {}
    ret_dict["receive_time"] = str(receive_time_str)
    ret_dict["receive_time_epoch"] = str(receive_time_epoch)
    if ping_output.find("Unreachable")>0 or ping_output.find("No route to host")>0:
        ret_dict["time"] = -1
        ret_dict["time_units"] = "?"
        ret_dict["bytes_received"] = -1
        ret_dict["payload_size"] = -1
        ret_dict["ttl"] = -1
        ret_dict["sequence"] = -1
    else:
        toks = ping_output.split()
        # print(f"line0 is: {toks}")
        ret_dict["bytes_received"] = int(toks[0])
        seq_string = toks[-4]
        ttl_string = toks[-3]
        time_string = toks[-2]
        # ret_dict["send_time"] = str(send_time)
        ret_dict["payload_size"] = payload_size
        ret_dict["sequence"] = int(seq_string.split("=")[1])
        ret_dict["ttl"] = int(ttl_string.split("=")[1])
        ret_dict["time"] = float(time_string.split("=")[1])
        ret_dict["time_units"] = toks[-1]

        time_multiplier = 0
        if ret_dict["time_units"]=="ms":
            time_multiplier = 1000
        elif ret_dict["time_units"]=="s":
            time_multiplier = 1

        ret_dict["transmit_time_abs"] = receive_time_epoch - (ret_dict["time"]/time_multiplier)
        tmp = receive_time_epoch - (ret_dict["time"]/time_multiplier)
        ret_dict["transmit_time_abs_str"] = datetime.datetime.fromtimestamp(tmp).strftime('%Y-%m-%d %H:%M:%S.%f')
        ret_dict["transmit_time_rel"] = reltime.get_reltime() - (ret_dict["time"]/time_multiplier)

    return(ret_dict)


def otherway(args):
    if args.influxdb:
        influx_writer = influxdb_writer()

    try:
        c = statsd.StatsClient('monitor-statsd_exporter-1', 9125, prefix='latency_monitor')
    except Exception as e:
        print("Can't find monitor-statsd_exporter-1 so no statsd exporting.")
        c = None

    cmd = ['ping', '-c', str(args.count)]
    if args.interval!=1.0:
        cmd += ['-i', args.interval]
    if args.use_ipv4:
        cmd += ["-4"]
    cmd += [args.target]

    print(f"cmd is: {cmd}")
    # Start the ping process
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    # Process and print the output lines as they come in
    hostname = socket.gethostname()
    done = False
    for line in process.stdout:
        line = line.strip().rstrip()
        #print(f"Got a line: {line}")
        if line[0:4] == "PING":
            toks = line.split()
            # payload_size = int(toks[-3])
            payload_size = -1
            continue
        if  len(line)<5 or done:
            done = True
            continue

        ret = output_to_dict(line, payload_size, str(datetime.datetime.now()), time.time())
        ret["source"] = hostname
        ret["target"] = args.target
        if args.verbose:
            print(f"{ret}")
        if c==None:
            print(ret)

        if c is not None:
            c.gauge(f"latency", ret["time"], tags={"Source2":hostname, "Target2": args.target})

        #
        # Write to influxdb.  This demonstrates high-resolution logging (as opposed to the
        # lower resolution when the data has to go through statsd then prometheus scraping
        # statsd, then grafana scraping prometheus).
        #
        if args.influxdb:
            if "transmit_time_abs_str" in ret:
                influx_writer.write_value2(ret["transmit_time_abs_str"], ret["time"], ret["time_units"],
                                          extra_tags = {"src": hostname, "dst": args.target,
                                                        "xmit_rel": ret["transmit_time_rel"]})

    # Wait for the process to finish
    process.wait()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="www.google.com")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--use-ipv4", action="store_true", default=False)
    parser.add_argument("--influxdb", action="store_true", default=False, help="Write to influxDB.")
    parser.add_argument("--verbose", action="store_true", default=False)
    args = parser.parse_args()

    otherway(args)




#c = statsd.StatsClient('localhost', 9125, prefix='netemcontroller')
##c.incr('bar')  # Will be 'foo.bar' in statsd/graphite.
##c.decr('bar')  # Will be 'foo.bar' in statsd/graphite.
#c.set('bar', 1)  # Will be 'foo.bar' in statsd/graphite.
#c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName1", "label2": "if1"})
#c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName1", "label2": "if2"})
#c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName2", "label2": "if1"})
#c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName2", "label2": "if2"})
#c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName3", "label2": "if1"})


