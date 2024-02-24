#!/usr/bin/env python3

import argparse
import statsd
import socket
import random
import subprocess
import json
import datetime

import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class influxdb_writer(object):
    def __init__(self):
        # token = os.environ.get("INFLUXDB_TOKEN")
        self.token = "uh0PBnHMtrECKmP7HjxYzQL5YM_yRZfqHaIYXafT0a4w2on70Tc6ezCt0Q0hevlY_k2mHdldLDfnqMiB_a4s9A=="
        self.org = "netsim"
        self.url = "http://influxdb2:8086"

        self.client = influxdb_client.InfluxDBClient(url=self.url, token=self.token, org=self.org)

        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
    
    def write_value(self, src, dst, val, units):
        dictionary = {
            "measurement": "latency",
            "tags": {"src": src, "dst": dst},
            "fields": {"value": float(val), "units": str(units)},
        }
        print(f"Logging to influxdb: {dictionary}")
        ret = self.write_api.write(bucket="netsim", org="netsim", record=dictionary)
        print(f"Result of influxdb write: {ret}")

# kscott@nucbuntu:~/Projects/netsim/Test$ ./latency_monitor.py
# PING www.google.com(mad41s04-in-x04.1e100.net (2a00:1450:4003:800::2004)) 56 data bytes
# 64 bytes from mad41s04-in-x04.1e100.net (2a00:1450:4003:800::2004): icmp_seq=1 ttl=118 time=7.61 ms

def output_to_dict(ping_output, payload_size, receive_time):
    print(f"in output_to_json: {ping_output} -- {receive_time}")
    ret_dict = {}
    ret_dict["receive_time"] = str(receive_time)
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
    cmd += [args.target]

    print(f"cmd is: {cmd}")
    # Start the ping process
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)

    # Process and print the output lines as they come in
    hostname = socket.gethostname()
    done = False
    for line in process.stdout:
        print(f"Got a line: {line}")
        if line[0:4] == "PING":
            toks = line.split()
            # payload_size = int(toks[-3])
            payload_size = -1
            continue
        if  len(line)<5 or done:
            done = True
            continue

        ret = output_to_dict(line.strip(), payload_size, str(datetime.datetime.now()))
        ret["source"] = hostname
        ret["target"] = args.target
        if args.verbose:
            print(f"logging the following: {ret}")
        if c==None:
            print(json.dumps(ret, indent=2))

        if c is not None:
            c.gauge(f"latency", ret["time"], tags={"Source2":hostname, "Target2": args.target})

        #
        # Write to influxdb.  This demonstrates high-resolution logging (as opposed to the
        # lower resolution when the data has to go through statsd then prometheus scraping
        # statsd, then grafana scraping prometheus).
        #
        if args.influxdb:
            influx_writer.write_value(hostname, args.target, ret["time"], ret["time_units"])

    # Wait for the process to finish
    process.wait()

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="www.google.com")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count", type=int, default=10)
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


