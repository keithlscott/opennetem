#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import os
import stat
import sys
import docker
import shutil
import threading
import concurrent
import subprocess
import math
import re

import urllib3
import json
import datetime
import time
import argparse
import opennetem.topology as topology
import opennetem.utilities as utilities
import opennetem.node as node
import opennetem.clean_containers as clean_containers
import opennetem.network as opennetemnetwork

import statsd

import logging
import opennetem.my_logging as my_logging
import pandas

from influxdb_client import Point

import opennetem.opennetem_tools.netem_reltime as netem_reltime


# logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')

# logger = netem_logging.get_sublogger("scenario")

#
# Scenario File (JSON)
#
# {"Scenario":
#     "Metadata": {},
#     "topology_filename": "filename"
#   "topology_sheetname": "SheetName"
# }


#
# Read a NetEm scenario from a JSON file and instantiate docker containers for the
# various nodes.

def netem_read_json_file(filename):
    with open(filename, "r") as fp:
        data = fp.read()
    return(json.loads(data))


def set_permissions(file_path):
    os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE | \
                stat.S_IRGRP | stat.S_IWGRP  | \
                stat.S_IROTH | stat.S_IWOTH)


def run_on_host(command):
    tmp_command = ["/bin/bash", "-c", command]
    mylogger = my_logging.get_sublogger("scenario.opennetem")
    mylogger.info(f"running command '{tmp_command}' on host.")
    subprocess.run(tmp_command)
    return


class netem_scenario(object):
    def __init__(self, args={}):
        self.logger = my_logging.get_sublogger("scenario", parent="opennetem")

        self.info_dir = "/var/run/opennetem"

        if os.getuid()!=0:
            self.logger.warning("You probably want to run this as root in order to be able to modify link parameters.")
            self.logger.warning("Abort or Continue (A/c)")
            res = str(input())
            if len(res)==0 or res[0]=="C" or res[0]=="c":
                self.logger.warning("Continuing as non-root user.")
            else:
                self.logger.fatal("Canceling due to not being root.")
                sys.exit(0)

        # Save our pid to self.info_dir.
        try:
            os.makedirs(self.info_dir, mode = 0o777, exist_ok=True)
            with open(f"{self.info_dir}/pid", "w") as fp:
                fp.write(f"{os.getpid()}")
            set_permissions(f"{self.info_dir}/pid")

        except Exception as e:
            print(f"Can't make info dir {self.info_dir} and create pid file: {e}")
            sys.exit(-1)
            pass

        self.logger.info(f"instantiating netem_scenario object; args = {args}")
        self.args = args
        self.client = docker.from_env()
        self.scenario_dict = None  # Dictionary describing scenario
        self.topology =      None  # netem_topology object describing time-variant topology
        self.nodes = {}           # Keyed by node_name, data is netem container object
        self.networks = {}       # keyed by net_name, data is docker network object
        self.container_info = {}   # Keyed by container name, contains 'ip addr show' info from containers
        self.host_network_info = []# List if 'ip addr show' info for host interfaces augmented with container and network names
        self.install_dir = os.path.dirname(os.path.realpath(__file__))
        self.instance_info = None
        self.logger.info(f"Opennetem install path: {self.install_dir}")
        self.statsd_client = statsd.StatsClient('localhost', 9125, prefix='netem_scenario')
        self.influxdb_support = utilities.influxdb_support()

        self.last_figure_time = None # Time of the last topology figure injected into the database.

        # Try to see if there's an existing set of containers / networks running and if
        # so give the user the option of killing them or cancelling.
        print(f"++++++++++++++++ ")
        utilities.check_running(self.args['force_clean'])

        self.reltime = netem_reltime.Reltime()

        return


    def load_scenario(self, scenario_filename):
        self.logger.info("Loading scenario file {scenario_filename}")
        self.scenario_dict = netem_read_json_file(scenario_filename)
        # Merge global node configs into each of the nodes' configs
        global_config = self.scenario_dict["node_configs"]["__global"] if "__global" in self.scenario_dict["node_configs"] else {}

        # Merge in global_config info with current node config
        for node in self.scenario_dict["node_configs"]:
            self.logger.debug(f"Doing mounts for node {node}")
            if node=="__global":
                continue
            for key in global_config:
                if key not in self.scenario_dict["node_configs"][node]:
                    self.scenario_dict["node_configs"][node][key] = global_config[key].copy()
            
            if "mounts" in global_config and ("mounts" not in self.scenario_dict["node_configs"][node]):
                self.logger.debug(f"Setting mount list for node {node} to []")
                self.scenario_dict["node_configs"][node]["mounts"] = []
            else:
                self.logger.debug(f"node {node} already has mount list: {self.scenario_dict['node_configs'][node]['mounts']}")

            self.logger.info(f"global_config['mounts'] is: {global_config['mounts']}")
            # tmp = list(global_config["mounts"]).copy()
            # for the_mount in tmp:
            #     logger.info(f"global_config['mounts'] is now {global_config['mounts']}")
            #     logger.info(f"Adding global mount {the_mount} to {node}'s mount list")
            #     self.scenario_dict["node_configs"][node]["mounts"] += [the_mount]

            self.logger.info(f"After updating with global_cofig {node}'s config is now:\n{self.scenario_dict['node_configs'][node]}")

        self.topology = topology.time_variant_topology(self)
        if self.scenario_dict["topology_filename"] != None:
            self.topology.read_topofile()
        self.logger.info(f"Scenario {scenario_filename} loaded.")
        self.scenario_dir = os.path.dirname(os.path.realpath(scenario_filename))
        self.logger.info(f"Scenario file path: {self.scenario_dir}")

        #
        # Generate png files for expected network connectivity over time and
        # make a list of pairs [[time, base64_of_figure], ...]
        #
        known_positions = {}
        for node in self.scenario_dict["node_configs"]:
            if node=="__global":
                continue
            print(self.scenario_dict["node_configs"][node])
            if "position" in self.scenario_dict["node_configs"][node]:
                known_positions[node] = self.scenario_dict["node_configs"][node]["position"]
        if known_positions == {}:
            known_positions = None

        opennetemnetwork.make_topology_figures(self.topology.df,
                                               "./topology_images",
                                               known_positions)
        self.topology_figures = opennetemnetwork.base64_figures("./topology_images")


    def list_networks(self) -> list[str]:
        """Return a list of the network names in the scenario."""
        networks = []
        for node in self.scenario_dict["node_configs"]:
            if "networks" in self.scenario_dict["node_configs"][node]:
                for net in self.scenario_dict["node_configs"][node]["networks"]:
                    if net not in networks:
                        networks += [net]
        return(networks)
    

    def instantiate_one_node(self, node_name: str, node_info: dict) -> None:
        "Instantiate a new Docker container representing a node in the network."
        tmp_node = node.opennetem_node(self, node_name, node_info)
        self.nodes[node_name] = tmp_node
        return
    

    def instantiate_nodes(self):
        # Note that global node_configs should have already been merged into the individual
        # nodes' configs
        for node_name in self.scenario_dict["node_configs"]:
            if node_name=="DEFAULT" or node_name=="__global":
                continue
            self.instantiate_one_node(node_name, self.scenario_dict["node_configs"][node_name])

        # Start the containers
        self.logger.info("Starting containers.")
        for node in self.nodes:
            self.nodes[node].container.start()
            self.nodes[node].rename_interface("eth0", "dock")

        self.logger.info("Done starting containers.")

        # Try to connect containers to monitor network
        self.connect_containers_to_monitor_network()


    def connect_containers_to_monitor_network(self):
        self.logger.info("Connecting containers to monitor network.")
        try:
            monitor_network = self.client.networks.get("monitor_default")
        except Exception as e:
            self.logger.info("Something went wrong getting monitor network (monitor stack not up?)")
            self.logger.info(f"  {e}")
            return
        
        for node in self.nodes:
            try:
                # Connect node to monitor network
                the_node = self.nodes[node]
                monitor_network.connect(the_node.container)

                # Change the name of the node's interface on the monitor network to 'mon'
                return_code, node_if_info = the_node.container.exec_run("ip --json addr show")
                node_if_info_json = json.loads(node_if_info)
                the_if = node_if_info_json[-1]["ifname"]
                the_node.rename_interface(the_if, "mon")
                # the_container.exec_run(f"ip link set dev {the_if} down")
                # the_container.exec_run(f"ip link set dev {the_if} name mon")
                # the_container.exec_run(f"ip link set dev mon up")

            except Exception as e:
                self.logger.warning(f"Something went wrong connecting node {self.nodes[node].container.name} to monitor network.")
                self.logger.warning(f"  {e}")        
        self.logger.info("Done connecting containers to monitor network.")


    def instantiate_docker_infrastructure(self):
        # Remove all files under var/ (local storage for nodes during simulation)
        # then recreate var so nodes will have a thing to mount.
        # Copy the scenario file into var with a given name (scenario.json)

        self.logger.info(f"instantiate_docker_infrastructure self.args = {self.args}")
        # shutil.rmtree(f"{self.scenario_dir}/netem", ignore_errors=True)
        os.makedirs(f"{self.scenario_dir}/mounts/global", mode = 0o777, exist_ok=True)
        shutil.copy(self.args['scenario_file'], f"{self.scenario_dir}/mounts/global/scenario.json")

        #
        # Instantiate nodes and links (all possible) with initial state disconnected
        #
        self.logger.info("Instantiating nodes and networks")
        self.instantiate_nodes()
        self.topology.instantiate_networks()


    class link_management_thread(threading.Thread):
        """Handle processing commands for all links whose (src,dst) pairs are in the 'node_pairs' init keyword arg.
        
        Node pairs should be a list of (from, to) node names e.g.:
            [('netem_node_a', 'netem_node_b'), ('netem_node_b', 'netem_node_a')]

        The caller needs to ensure that all links are assigned to exactly one
        link_management_thread."""

        def __init__(self, group=None, target=None, name=None,
               args=(), kwargs=None, verbose=None):
            self.logger = my_logging.get_sublogger(f"linkManagement", parent="opennetem.scenario")
            super(netem_scenario.link_management_thread,self).__init__(group=group, target=target, 
                            name=name,)
            # self.logger.info(f"Init link_management_thread for node_pairs {kwargs['node_pairs']}")
            # self.logger.info(f"Init link_management_thread topology_df is:\n{kwargs['topology_df']}")
            # self.logger.info(f"Init link_management_thread short_mapping is:\n{kwargs['scenario'].topology.iface_info}")
               
            self.args = args
            self.kwargs = kwargs
            self.scenario = self.kwargs["scenario"]
            self.node_pairs = kwargs["node_pairs"]
            self.iface_info = kwargs["iface_info"]
            self.topology_df = kwargs["topology_df"]
            
            src_values, dst_values = zip(*kwargs["node_pairs"])
            result = kwargs['topology_df'][kwargs['topology_df']['source'].isin(src_values) & 
                             kwargs['topology_df']['dest'].isin(dst_values)]

            self.sorted_result = result.sort_values(by="time")
            # self.logger.info(f"Init link_management_thread sorted_result is:\n {self.sorted_result}")


        def run(self):
            #logger = my_logging.get_sublogger("LinkManagement")
            # logger = my_logging.get_sublogger("LinkManagement")
            self.logger.info(f"Link management thread started for {self.node_pairs}")
            # self.logger.info(f"self.sorted_result is:\n{self.sorted_result}")

            def remove_dead_threads2():
                for t in self.threads:
                    if not t.is_alive():
                        self.logger.info(f"Command thread {self.node_pairs} is no longer alive; removing it.")
                        t.join()
                        self.threads.remove(t)

            self.threads = []
            cur_row = 0
            while cur_row < len(self.sorted_result):
                next_command = self.sorted_result.iloc[cur_row]
                next_time = self.scenario.instance_info["start_time"] + next_command["time"]
                self.logger.info(f"Next link change for {self.node_pairs} is at {next_command['time']} {next_time}; cur_time is {time.time()}; waiting.")
                while time.time()<next_time:
                    remove_dead_threads2()
                    time.sleep(next_time-time.time())
                self.logger.info(f"Launching NEW LinkProcessingThread to make link change for {self.node_pairs}")
                # host_interface = self.scenario.topology.iface_info[(f"netem_{next_command['source']}", f"netem_{next_command['dest']}")]
                host_interface = self.scenario.topology.iface_info[(f"{next_command['source']}", f"{next_command['dest']}")]

                foo = threading.Thread(target=self.scenario.change_link_params, name=f"LinkProcessingThread for {next_command['source']}-{next_command['dest']} at {next_command['time']} on list interface {host_interface}",
                           args=(next_command, host_interface,))
                foo.start()
                self.threads += [foo]
                remove_dead_threads2()
                cur_row += 1

            remove_dead_threads2()
    
        def status(self):
            self.remove_dead_threads2()
            ret = {}
            ret["active_threads"] = []
            for t in self.threads:
                ret["active_threads"] += t.__name__


    # This is the LinkProcessingThread invoked to change link parameters.
    #
    # command_row is a dataframe row from the topology df
    # This is the 'target' function of a threading.Thread instance, so the fact that we're running
    # the subprocess tc qdisc change command synchronously shouldn't be a problem, I don't think.
    def change_link_params(self, command_row: pandas.DataFrame, host_interface: str) -> None:
        """This is invoked as a thread to change link parameters.
        command_row is a dataframe row from the topology df
        Since this is the 'target' function of a threading.Thread instance, so the fact that we're running
        the subprocess tc qdisc change command synchronously shouldn't be a problem, I don't think.       
        """

        # logger = my_logging.get_sublogger("scenario")
        my_logger = my_logging.get_sublogger("link_management", parent="opennetem.scenario")

        # We might normalize the delay and loss values, and pandas gets upset if we try to
        # set the value on a copy of a DataFrame slice
        tmp2 = command_row.copy()

        # tc qdisc change dev veth7f21235 root netem delay 100ms loss 2%
        if 'loss' not in tmp2 or tmp2['loss']=="":
            # command_row['loss'] = "0%"
            tmp2['loss'] = "0%"

        if type(command_row['delay']) == type(""):
            pass
        else:
            tmp2['delay'] = "0s"
            tmp2['loss'] = "100%"

        my_logger.info(f"change_link_params {command_row['source']}-{command_row['dest']} executing change: {tmp2.to_dict()}")
        my_logger.debug(f"change_link_params {command_row['source']}-{command_row['dest']} host interface is {host_interface}")

        result = subprocess.run(f"/usr/sbin/tc qdisc change dev {host_interface} root netem delay {tmp2['delay']} rate {tmp2['rate']} loss {tmp2['loss']}".split(),
                                 capture_output=True)
        my_logger.info(f"result of link change command {tmp2.to_dict()} for {command_row['source']}-{command_row['dest']}: {result.stdout.decode('utf-8')}")
        
        other_fields = {"source": command_row["source"],
                        "dest":   command_row["dest"],
                        "delay":  tmp2["delay"],
                        "rate":   tmp2["rate"],
                        "loss":   tmp2["loss"]}
        self.influxdb_support.write_value("topology_change_times",
                                    f"Topology change at t={self.reltime.get_reltime():.3f}",
                                    other_fields_dict=other_fields)
        
        self.log_current_time()

        return


    def update_topology_image(self) -> None:
        """Write the current topology image to influxdb if necessary."""

        if len(self.topology_figures)>0 and \
                (self.last_figure_time==None or self.topology_figures[0][0]<=self.reltime.get_reltime()):
            self.influxdb_support.write_value("topology_image", self.topology_figures[0][1], other_fields_dict={})
            self.topology_figures = self.topology_figures[1:]
            self.last_figure_time = self.reltime.get_reltime()


    class cmd_processing_thread(threading.Thread):
        """Process in-node commands
        
        This thread handles processing all commands for all nodes in the node_list
        keyword argument.  This might be just one node, or we might assign multiple
        nodes to a single command processing thread (might be useful if we have
        hundreds of nodes, e.g.)

        The caller needs to ensure that enough cmd_processing_threads are instantiated
        to cover all the nodes."""

        #
        # We first run through all the commands and pick out only those that we
        # manage and save them in our local command_list
        #
        # We then hang around until we've launched all of the commands.
        #
        # FIXME: we exit after launching our last command, which may have started
        #        a long-running command on the host (e.g. on_mon_bplist).  We really
        #        need (I think) to pass in something more permanent (the scenario?)
        #        so we can seriously kill those threads later.  But there's no good way
        #        to forceably kill a thread https://discuss.python.org/t/how-kill-a-thread/42959/2
        #        so.....
        #        Maybe it's a requirement that long-running host processes like on_bpstats
        #        exit when there are no nodes.
        #
        def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
            #self.logger = my_logging.get_sublogger(f"cmd_processing_thread")
            self.logger = my_logging.get_sublogger(f"cmd_processing_thread", parent="opennetem.scenario")
            super(netem_scenario.cmd_processing_thread,self).__init__(group=group, target=target, 
                            name=name,)
            self.args = args
            self.kwargs = kwargs

            self._stop_event = threading.Event()  
            self.client = docker.from_env()
            self.scenario = self.kwargs["scenario"]
            self.node_list = self.kwargs["node_list"]
            self.command_list = self.kwargs["command_list"]

            self.logger.info(f"Command processing thread {self.name} starting command processing thread for nodes: {self.node_list}")

            self.my_commands = [] # command_list dictionaries augmented with node_name elements

            # self.instance_info = netem_utilities.robustly_read_json_file(f"{self.scenario.scenario_dir}/var/global/instance_info.json")

            #
            # Build the list of commands this thread needs to handle.
            # Note that these may be for multiple nodes (if len(self.node_list)>1)
            #
            for the_command in self.command_list:
                for container_name in the_command["nodes"]:
                    self.logger.debug(f"Thread {self.name} checking to see if container {container_name} is one of mine {self.node_list}")
                    # containers = self.client.containers.list(all=True, filters={"label": ["netem_node=True"]})
                    # containers = self.client.containers.list(filters={"name": "netem_"+container_name})
                    # self.logger.info(f"Container list is: {[c.name for c in containers]}")
                    for n in self.node_list:
                        #for c1 in containers:
                        #if c1.name==n:

                        #
                        # See if the node name matches a target node of the command.
                        #
                        do_this_node = False
                        for entry in the_command["nodes"]:
                            if (entry=="*"):
                                entry = ".*"
                            pattern = re.compile(entry)
                            if pattern.match(n):
                                do_this_node = True
                                break

                        if not do_this_node:
                            continue

                        self.logger.info(f"Thread {self.name} is handling command {the_command} for node {n}")
                        tmp = the_command.copy()

                        # Do NETEM_ADDR replacement========================
                        # Define the regular expression pattern to extract A and B parameters
                        #
                        pattern = r'NETEM_ADDR\(([^,]+),\s*([^)]+)\)'

                        # Use re.findall to find all matches of the pattern in the input string
                        matches = re.findall(pattern, tmp["command"])

                        # If matches are found, extract A and B parameters
                        for m in matches:
                            # Extract A and B parameters from the first match
                            node = m[0]
                            network = m[1]

                            # Define the replacement string
                            replacement_string = utilities.get_ip_addr(self.scenario, node, network)
                            
                            # Define the regular expression pattern to match FUNC(A, B)
                            pattern = r'NETEM_ADDR\([^)]+\)'

                            # Use re.sub to substitute the pattern with the replacement string
                            tmp["command"] = re.sub(pattern, replacement_string, tmp["command"])
                            self.logger.info(f"cmd replacement NETEM_ADDR; cmd is now {tmp['command']}")
                        # Done with NETEM_ADDR f-strings========================

                        #tmp["command"] = eval(f"""f'{tmp["command"]}'""")
                        self.logger.debug(f"Node {n} after fstring replacement; cmd is now {tmp['command']}")

                        tmp["node_name"] = n
                        if n=="HOST":
                            the_container = None
                        else:
                            the_container = self.client.containers.list(filters={"name": n})[0]

                        tmp["container"] =  the_container
                        tmp["command"] = tmp["command"].replace("NETEM_NODE_NAME", n)     # Replace NETEM_NODE_NAME with the node name
                        tmp["command"] = tmp["command"].replace("NETEM_START_TIME", str(int(self.scenario.instance_info["start_time"])))     # Replace NETEM_START_TIME with the scenario start time
                        tmp["command"] = f"""/bin/bash -c '{tmp["command"]}'"""
                        self.my_commands += [tmp]
            
            # Sort the commands for each node in time order
            self.my_commands.sort(key=lambda x: x["time"])

            self.logger.info(f"Thread {self.name} done preprocessing commands")


        def stop(self):
            self.logger.info(f"stop() called on command processing thread {self.name}")
            self._stop_event.set()
        

        # Run function for the cmd_processing_thread class
        def run(self):
            def remove_dead_threads():
                for t in self.threads:
                    if not t.is_alive():
                        self.logger.debug(f"Thread {t.name} command thread is no longer alive; removing it.")
                        t.join()
                        self.threads.remove(t)

            self.threads = []
            #
            # Maybe while(len(self.my_commands)>0 or len(self.threads)>0) and sleep 5 if len(self.my_commands==0)
            while len(self.my_commands)>0:
                next_command = self.my_commands[0]
                next_time = self.scenario.instance_info["start_time"] + next_command["time"]
                self.logger.info(f"{self.name}: next command for {next_command['node_name']} is at time {next_time}; cur_time is {time.time()}; waiting.")
                while time.time()<next_time:
                    remove_dead_threads()
                    time.sleep(next_time-time.time())
                self.logger.info(f"Thread {self.name} executing command {next_command} on node {next_command['node_name']}")

                if next_command["container"]!=None:
                    foo = threading.Thread(name=f"{next_command['container'].name} : {next_command['command']}",
                            target=next_command["container"].exec_run,
                            args=(next_command["command"],))
                    foo.start()
                    self.threads += [foo]
                    self.my_commands = self.my_commands[1:]
                else:
                    # Run command on host
                    foo = threading.Thread(name=f"HOST: {next_command['command']}",
                            target=run_on_host,
                            args=(next_command["command"],))
                    foo.start()
                    self.threads += [foo]
                    self.my_commands = self.my_commands[1:]

                remove_dead_threads()

                if self._stop_event.is_set():
                    self.logger.info("Command processing thread notes that it is stopped.")
                    break

            remove_dead_threads()

            self.logger.info(f"Thread {self.name} done running (FIXME: may have left childen).")


        def status(self):
            self.remove_dead_threads()
            ret = {}
            ret["node_list"] = self.node_list
            ret["active_threads"] = []
            for t in self.threads:
                ret["active_threads"] += t.__name__


    # The netem_scenario class isn't really a *thread*, but we do have this run
    # method
    def run(self) -> None:
        self.logger.debug("Start of scenario run loop.")
        
        self.command_threads = []
        self.link_management_threads = []

        start_on_minute = False
        if "start_on_minute" in self.scenario_dict:
            start_on_minute = self.scenario_dict["start_on_minute"]
        if "start_on_minute" in self.args and self.args["start_on_minute"]:
            start_on_minute = True

        start_delta = 10
        if "start_delta" in self.args:
            start_delta = int(self.args["start_delta"])
        elif "start_delta" in self.scenario_dict:
            start_delta = float(self.scenario_dict["start_delta"])
        
        start_time = int(math.ceil(time.time())+start_delta)
        if start_on_minute:
            start_time = int((math.ceil(time.time())+start_delta)/60)*60+60
            
        self.reltime.reset(start_time)
        self.logger.info(f"Run will start at time time {start_time}; cur_time is {time.time()}.")
        self.log_current_time()

        the_dict = {"start_time": start_time,
                    "start_time_long": str(datetime.datetime.now()+datetime.timedelta(0,start_delta))
                   }
        self.instance_info = the_dict
        with open(f"{self.scenario_dir}/mounts/global/instance_info.json", "w") as fp:
            fp.write(json.dumps(self.instance_info, indent=2))

        with open(f"{self.scenario_dir}/mounts/global/container_info.json", "w") as fp:
            fp.write(json.dumps(self.container_info, indent=2))

        #
        # Write the container_info and scenario to /var/run/opennetem in the host
        #
        try:
            with open(f"{self.info_dir}/container_info.json", "w") as fp:
                fp.write(json.dumps(self.container_info, indent=2))
            set_permissions(f"{self.info_dir}/container_info.json")
        except Exception as e:
            self.logger.warning(f"Can't write container_info.json to {self.info_dir}/container_info.json")

        try:
            with open(f"{self.info_dir}/scenario.json", "w") as fp:
                fp.write(json.dumps(self.scenario_dict, indent=2))
            set_permissions(f"{self.info_dir}/scenario.json")
        except Exception as e:
            self.logger.warning(f"Can't write scenario.json to /var/run/opennetem/scenario.json")
            self.logger.warning(f"{e}")
            time.sleep(5)
            pass

        # Write the network names into the influxdb database so we can use them in dashboards
        self.influxdb_support.delete('1970-01-01T00:00:00Z', '2050-04-27T00:00:00Z',
                                    measurement_name="network_names", bucket="netem", org="netem")
        for network_name in list(self.scenario_dict["networks"].keys()):
            self.influxdb_support.write_value(measurement_name="network_names", measurement_val=network_name,
                                        tags_dict = {},
                                        other_fields_dict = {})

        # Write the node names into the influxdb database so we can use them in dashboards
        self.influxdb_support.delete('1970-01-01T00:00:00Z', '2050-04-27T00:00:00Z',
                                    measurement_name="node_names", bucket="netem", org="netem")
        for node_name in list(self.scenario_dict["node_configs"].keys()):
            self.influxdb_support.write_value(measurement_name="node_names", measurement_val=node_name,
                                        tags_dict = {},
                                        other_fields_dict = {})
        
        #
        # Start command_processing threads.  Need to ensure that the various node_lists
        # here cover (without duplication) all the nodes
        #
        # For the moment it's just one node per processing thread, but we might need to
        # aggregate multiple nodes per thread if we have a LOT of nodes.
        #
        self.logger.info(json.dumps(the_dict, indent=2))
        for c in self.scenario_dict["node_configs"]:
            if c=="__global":
                continue
            t = self.cmd_processing_thread( name=f"cmd_processing_thread",
                                            kwargs={'scenario':self,
                                                   'node_list':[c],
                                                   'command_list':self.scenario_dict["commands"]})
            t.start()
            self.command_threads += [t]

        # A special thread for executing commands on the host (not in containers)
        t = self.cmd_processing_thread( name=f"cmd_processing_thread for HOST",
                                        kwargs={'scenario':self,
                                                'node_list':["HOST"],
                                                'command_list':self.scenario_dict["commands"]})
        t.start()
        self.command_threads += [t]

        #
        # Start the link characteristic processing threads.  Need to ensure that the various
        # (src,dst) lists here cover (without duplication) all of the links.
        #
        # Initial take: one link management thread per link.
        #
        self.logger.info("Starting link_management_thread(s).")
        link_pairs = self.topology.list_link_pairs()
        for e in link_pairs:
            # self.logger.info(f"Instantiating link management thread for {e}")
            node_pairs = [e]
            t = self.link_management_thread(name=f"link_management_thread for {node_pairs}",
                                            kwargs={'scenario': self,
                                                    'node_pairs': node_pairs,
                                                    'iface_info': None,
                                                    'topology_df': self.topology.df})
            t.start()
        self.link_management_threads += [t]

        #
        # Wait for the start time.  Note that per-node commands may be executing in
        # the interim.
        #
        WAIT_TIME_THRESHOLD = 0.002
        while time.time()<the_dict["start_time"]:
            self.update_topology_image()
            time_needed = max(the_dict["start_time"]-time.time(), 0)
            self.logger.info(f"Waiting to start {start_time-time.time():.2f}...")
            self.log_current_time()
            if time_needed>1 and (time_needed-int(time_needed)>WAIT_TIME_THRESHOLD):
                time.sleep(time_needed-int(time_needed)-WAIT_TIME_THRESHOLD)
            else:
                time.sleep(min(1, time_needed))
        self.logger.info("Time starts.")
        try:
            self.statsd_client.gauge("netem_event", 1, tags={"event": "t=0"})
        except Exception as e:
            self.logger.warning(f"Logging netem_event to statsd gauge yielded error: {e}")

        #
        # Wait for everything to be done
        #
        next_print = time.time()+5
        while (time.time()-start_time)<=self.topology.df["time"].max()+1:
            cur_time = time.time()
            if cur_time>=next_print:
                self.logger.info(f"abs_time: {cur_time}  rel_time: {self.reltime.get_reltime():.6f} -- waiting for {self.topology.df['time'].max()}")
                next_print += 5
            time_needed = next_print-cur_time
            self.log_current_time()

            self.update_topology_image()

            time.sleep(min(time_needed,1)+WAIT_TIME_THRESHOLD)
        
        self.logger.info(f"Joining cmd_processing threads ({len(self.command_threads)})")
        self.join_threads(self.command_threads)

        self.logger.info(f"Joining link processing threads ({len(self.link_management_threads)})")
        self.join_threads(self.link_management_threads)


    def join_threads(self, thread_list):
        for t in thread_list:
            self.logger.info(f"    {t.name}")
        for t in self.command_threads:
            t.stop()
            if t.is_alive():
                while t.is_alive():
                    t_status = t.status()
                    self.logger.info(f"Joining {t.name} with {len(t_status['active_threads'])} threads")
                    t.join(5)
            else:
                self.logger.info(f"Thread {t.name} is not alive.")
                self.logger.debug(f"Joined {t.name}")


    def log_current_time(self, the_value: None|float = None) -> None:
        """Log current time to influxDB measurement 'current_time'"""
        if the_value==None:
            the_value = int(self.reltime.get_reltime())

        self.logger.info(f"Logging current time as {the_value}")
        self.influxdb_support.write_value(measurement_name="current_time",
                    measurement_val=int(the_value),
                    tags_dict = {},
                    other_fields_dict = {})

    

def opennetem() -> None:
    """Main entry point for running an emulation"""
    global my_logging
    
    SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(f"{SOURCE_DIR}/opennetem_tools")

    logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')

    logger = logging.getLogger("opennetem")

    logger = my_logging.get_sublogger("scenario", parent="opennetem")

    SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))
    
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_file", nargs="?", default=None)
    parser.add_argument("--start_on_minute", action="store_true", default=False)
    parser.add_argument("--force_clean", default=False, action="store_true")
    parser.add_argument("--leave_containers", "-l", default=False, action="store_true")
    parser.add_argument("--cleanup", "-c", default=False, action="store_true")
    args = parser.parse_args()

    if args.cleanup:
        print(f"Removing docker containers and networks.")
        clean_containers.cleanup_all()
        sys.exit(0)

    if args.scenario_file==None:
        logger.fatal("Must provide a scenario file (JSON).")
        sys.exit(-1)

    opennetem_helper(args)


def opennetem_helper(args):
    print(f"in opennetem_helper args is: {args}")
    scenario_dir = os.path.dirname(os.path.realpath(args.scenario_file))

    # if "start_on_minute" not in args:
    #     args.start_on_minute = False
    # if "leave_containers" not in args:
    #     args.leave_containers = False
    
    my_logging.do_logging_config(scenario_dir)
    logger = logging.getLogger("opennetem.scenario")

    logger.info(f"opennetem begins")

    logger.info(f"Scenario file is {args.scenario_file}")
    logger.info(f"Leave_containers is {args.leave_containers}")

    foo = netem_scenario(args=vars(args))
    
    foo.load_scenario(args.scenario_file)

    foo.instantiate_docker_infrastructure()

    # Flush all the loggers, in particular the file logger.
    [h.flush() for h in logger.handlers]

    logger.debug(json.dumps(foo.container_info, indent=2))

    foo.run()

    # Unless asked to leave the infrastructure lying around, remove the containers
    # and networks.
    if not args.leave_containers:
        logger.info("Cleaning up containers now.")
        clean_containers.cleanup_all()

    # TODO: Really should go through all the nodes' mounts and catch those; this
    #       ASSUMES that they're all under the scenario directory.
    utilities.reset_ownership(scenario_dir)

    #
    # Remove our PID file
    #
    try:
        os.remove("/var/run/opennetem/pid")
    except Exception as e:
        logger.warning(f"Cannot remove pid file /var/run/opennetem/pid")

    foo.log_current_time(-1)
    logger.info(f"opennetem ends")


if __name__=="__main__":
    opennetem()
