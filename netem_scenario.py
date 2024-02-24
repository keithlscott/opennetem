#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import os
import sys
import docker
import shutil
import threading
import concurrent
import subprocess
import math

import json
import datetime
import time
import argparse
import netem_topology
import netem_utilities
import netem_node
import clean_containers
import statsd

import logging
import netem_logging

from influxdb_client import Point

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))

sys.path.append(f"{SOURCE_DIR}/netem_tools")
import netem_reltime


logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')

logger = netem_logging.get_sublogger("scenario")

#
# Scenario File (JSON)
#
# {"Scenario":
# 	"Metadata": {},
# 	"topology_filename": "filename"
#   "topology_sheetname": "SheetName"
# }


#
# Read a NetEm scenario from a JSON file and instantiate docker containers for the
# various nodes.

def netem_read_json_file(filename):
	with open(filename, "r") as fp:
		data = fp.read()
	return(json.loads(data))


class netem_scenario(object):
	def __init__(self, args={}):
		self.args = args
		self.client = docker.from_env()
		self.scenario_dict = None  # Dictionary describing scenario
		self.topology =      None  # netem_topology object describing time-variant topology
		self.nodes = {}		       # Keyed by node_name, data is netem container object
		self.networks = {}	       # keyed by net_name, data is docker network object
		self.container_info = {}   # Keyeb by container name, contains 'ip addr show' info from containers
		self.host_network_info = []# List if 'ip addr show' info for host interfaces augmented with container and network names
		self.install_dir = os.path.dirname(os.path.realpath(__file__))
		self.instance_info = None
		logger.info(f"Opennetem install path: {self.install_dir}")
		self.statsd_client = statsd.StatsClient('localhost', 9125, prefix='netem_scenario')
		self.influxdb_support = netem_utilities.influxdb_support()

		# Try to see if there's an existing set of containers / networks running and if
		# so give the user the option of killing them or cancelling.
		netem_utilities.check_running()

		self.reltime = netem_reltime.Reltime()

		return


	def load_scenario(self, scenario_filename):
		self.scenario_dict = netem_read_json_file(scenario_filename)
		self.topology = netem_topology.time_variant_topology(self)
		if self.scenario_dict["topology_filename"] != None:
			self.topology.read_topofile()
		logger.info(f"Scenario {scenario_filename} loaded.")
		self.scenario_dir = os.path.dirname(os.path.realpath(scenario_filename))
		logger.info(f"Scenario file path: {self.scenario_dir}")

		# if os.path.exists(f"{self.scenario_dir}/logging.conf"):
		# 	logging.config.fileConfig(f'{self.scenario_dir}/logging.conf')
		# 	logging.info(f"Reloading logging.config from scenario dir file {self.scenario_dir}/logging.conf")


	def list_networks(self):
		networks = []
		for node in self.scenario_dict["node_configs"]:
			if "networks" in self.scenario_dict["node_configs"][node]:
				for net in self.scenario_dict["node_configs"][node]["networks"]:
					if net not in networks:
						networks += [net]
		return(networks)
	

	def instantiate_one_node(self, node_name, node_info, global_info):
		node = netem_node.netem_node(self, node_name, node_info, global_info)
		self.nodes[node_name] = node
		return
	
	def instantiate_nodes(self):
		for node_name in self.scenario_dict["node_configs"]:
			global_config = None
			if "__global" in self.scenario_dict["node_configs"]:
				global_config = self.scenario_dict["node_configs"]["__global"]

			if node_name=="DEFAULT" or node_name=="__global":
				continue
			logger.info(f"instantiate_nodes making a node from {self.scenario_dict['node_configs'][node_name]}")
			self.instantiate_one_node(node_name, self.scenario_dict["node_configs"][node_name], global_config)

		# Start the containers
		logger.info("Starting containers.")
		for node in self.nodes:
			self.nodes[node].container.start()
			self.nodes[node].rename_interface("eth0", "dock")

		logger.info("Done starting containers.")

		# Try to connect containers to monitor network
		self.connect_containers_to_monitor_network()


	def connect_containers_to_monitor_network(self):
		logger.info("Connecting containers to monitor network.")
		try:
			monitor_network = self.client.networks.get("monitor_default")
		except Exception as e:
			logger.info("Something went wrong getting monitor network (monitor stack not up?)")
			logger.info(f"  {e}")
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
				logger.warning(f"Something went wrong connecting node {self.nodes[node].container.name} to monitor network.")
				logger.warning(f"  {e}")		
		logger.info("Done connecting containers to monitor network.")


	def instantiate_docker_infrastructure(self):
		# Remove all files under var/ (local storage for nodes during simulation)
		# then recreate var so nodes will have a thing to mount.
		# Copy the scenario file into var with a given name (scenario.json)
		shutil.rmtree(f"{self.scenario_dir}/netem", ignore_errors=True)
		os.makedirs(f"{self.scenario_dir}/netem/globals", mode = 0o777, exist_ok=True)
		shutil.copy(args.scenario_file, f"{self.scenario_dir}/netem/globals/scenario.json")

		#
		# Instantiate nodes and links (all possible) with initial state disconnected
		#
		logger.info("Instantiating nodes and networks")
		self.instantiate_nodes()
		self.topology.instantiate_networks()

		# Instantiate threads to deal with changing link characteristics
		# {('netem_node_a', 'netem_node_b'): 'veth3d4ca06',
		#  ('netem_node_b', 'netem_node_a'): 'vethf5f0f58',
		#  ('netem_node_b', 'netem_node_c'): 'veth97e4216',
		#  ('netem_node_c', 'netem_node_b'): 'vethf90daa8',
		#  ('netem_node_a', 'netem_node_c'): 'vethfccefe2',
		#  ('netem_node_c', 'netem_node_a'): 'veth74d17e4'
		# }


	#
	# This thread handles processing commands for all links whose (src,dst)
	# pairs are in the 'node_pairs' keyword arg.
	#
	# node_pairs should be a list of (from, to) node names e.g.:
	# [('netem_node_a', 'netem_node_b'), ('netem_node_b', 'netem_node_a')]
	#
	# The caller needs to ensure that all links are assigned to exactly one
	# link_management_thread.
	#
	class link_management_thread(threading.Thread):
		def __init__(self, group=None, target=None, name=None,
			   args=(), kwargs=None, verbose=None):
			super(netem_scenario.link_management_thread,self).__init__(group=group, target=target, 
							name=name,)
			logger.info(f"Init link_management_thread for node_pairs {kwargs['node_pairs']}")
			logger.info(f"Init link_management_thread topology_df is:\n{kwargs['topology_df']}")
			logger.info(f"Init link_management_thread short_mapping is:\n{kwargs['scenario'].topology.iface_info}")
			   
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
			logger.info(f"Init link_management_thread sorted_result is:\n {self.sorted_result}")


		def run(self):
			logger.info(f"Link management thread for {self.node_pairs} started.")
			logger.info(f"self.sorted_result is:\n{self.sorted_result}")

			def remove_dead_threads2():
				for t in self.threads:
					if not t.is_alive():
						logger.info(f"Thread {t.name} command thread is no longer alive; removing it.")
						t.join()
						self.threads.remove(t)

			self.threads = []
			cur_row = 0
			while cur_row < len(self.sorted_result):
				next_command = self.sorted_result.iloc[cur_row]
				next_time = self.scenario.instance_info["start_time"] + next_command["time"]
				logger.info(f"Thread {self.name}: next link change is at time {next_command['time']} {next_time}; cur_time is {time.time()}; waiting.")
				while time.time()<next_time:
					remove_dead_threads2()
					time.sleep(next_time-time.time())
				logger.info(f"Thread {self.name} launching NEW LinkProcessingThread to make link change")
				host_interface = self.scenario.topology.iface_info[(f"netem_{next_command['source']}", f"netem_{next_command['dest']}")]

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
	def change_link_params(self, command_row, host_interface):
		# tc qdisc change dev veth7f21235 root netem delay 100ms loss 2%
		if 'loss' not in command_row or command_row['loss']=="":
			command_row['loss'] = "0%"

		if type(command_row['delay']) == type(""):
			pass
		else:
			command_row['delay'] = "0s"
			command_row['loss'] = "100%"

		logger.info(f"change_link_params executing change: {command_row.to_dict()}")
		logger.info(f"change_link_params host interface is {host_interface}")

		result = subprocess.run(f"/usr/sbin/tc qdisc change dev {host_interface} root netem delay {command_row['delay']} rate {command_row['rate']} loss {command_row['loss']}".split(),
				 				capture_output=True)
		logger.info(f"result of link change command {command_row.to_dict()}: {result.stdout.decode('utf-8')}")
		
		# self.statsd_client.gauge("netem_event", 1, tags={"event": "link_change"})
		#
		# Log to influxdb so we can indicate the time of the link change.
		#
		# point = (
    	# 	Point("link_change")
    	# 		.tag("delay", command_row['delay'])
    	# 		.field("temp_value", 1)
  		# 	)
		# self.influxdb_support.write_point(point=point)

		tags_dict = {"source": command_row["source"],
			         "dest":   command_row["dest"]}
		other_params = {}
		# other_params = {"latency": command_row["delay"],
		# 				"delay": command_row["delay"],
		# 		  		"loss":  command_row["loss"],
		# 				"const": 4}
		self.influxdb_support.write_value(measurement_name="link_change", measurement_val=1,
									tags_dict = tags_dict,
									other_fields_dict = other_params)
		return


	#
	# This thread handles processing all commands for all nodes in the node_list
	# keyword argument.
	#
	# The caller needs to ensure that enough cmd_processing_threads are instantiated
	# to cover all the nodes.
	#
	class cmd_processing_thread(threading.Thread):
		def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
			super(netem_scenario.cmd_processing_thread,self).__init__(group=group, target=target, 
							name=name,)
			self.args = args
			self.kwargs = kwargs

			self.client = docker.from_env()
			self.scenario = self.kwargs["scenario"]
			self.node_list = self.kwargs["node_list"]
			self.command_list = self.kwargs["command_list"]

			logger.info(f"Thread {self.name} starting command processing thread for nodes: {self.node_list}")

			self.my_commands = [] # command_list dictionaries augmented with node_name elements

			# self.instance_info = netem_utilities.robustly_read_json_file(f"{self.scenario.scenario_dir}/var/globals/instance_info.json")

			#
			# Build the list of commands this thread needs to handle.
			# Note that these may be for multiple nodes (if len(self.node_list)>1)
			#
			for c in self.command_list:
				for container_name in c["nodes"]:
					logger.info(f"Thread {self.name} checking to see if container {container_name} is one of mine {self.node_list}")
					containers = self.client.containers.list(filters={"name": "netem_"+container_name})
					logger.info(f"Container list is: {[c.name for c in containers]}")
					for n in self.node_list:
						logger.info(f"  checking {n} against container list {[c.name for c in containers]}")
						for c1 in containers:
							if c1.name=="netem_"+n:
								logger.info(f"Thread {self.name} is handling command {c} for node {n} container {c1.name}")
								tmp = c.copy()
								tmp["node_name"] = "netem_"+n
								tmp["container"] = c1
								tmp["command"] = tmp["command"].replace("NETEM_NODE_NAME", n)     # Replace NETEM_NODE_NAME with the node name
								tmp["command"] = tmp["command"].replace("NETEM_START_TIME", str(int(self.scenario.instance_info["start_time"])))     # Replace NETEM_START_TIME with the scenario start time
								tmp["command"] = f"""/bin/bash -c '{tmp["command"]}'"""
								self.my_commands += [tmp]
			
			# Sort the commands for each node in time order
			self.my_commands.sort(key=lambda x: x["time"])

			logger.info(f"Thread {self.name} done preprocessing commands")

		# Run function for the cmd_processing_thread class
		def run(self):
			def remove_dead_threads():
				for t in self.threads:
					if not t.is_alive():
						logger.info(f"Thread {t.name} command thread is no longer alive; removing it.")
						t.join()
						self.threads.remove(t)

			self.threads = []
			while len(self.my_commands)>0:
				next_command = self.my_commands[0]
				next_time = self.scenario.instance_info["start_time"] + self.my_commands[0]["time"]
				logger.info(f"Thread {self.name}: next command is at time {next_time}; cur_time is {time.time()}; waiting.")
				while time.time()<next_time:
					remove_dead_threads()
					time.sleep(next_time-time.time())
				logger.info(f"Thread {self.name} executing command {self.my_commands[0]} on node {self.my_commands[0]['node_name']}")
				# Should probably 
				# result = self.client.containers.exec_run(next_command["container"])
				foo = threading.Thread(name=f"{next_command['container'].name} : {next_command['command']}",
						   target=next_command["container"].exec_run,
						   args=(next_command["command"],))
				foo.start()
				self.threads += [foo]
				self.my_commands = self.my_commands[1:]
				remove_dead_threads()

			remove_dead_threads()

		def status(self):
			self.remove_dead_threads()
			ret = {}
			ret["node_list"] = self.node_list
			ret["active_threads"] = []
			for t in self.threads:
				ret["active_threads"] += t.__name__

	# The netem_scenario class isn't really a thread, but we do have this run
	# method
	def run(self):
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
		logger.info(f"Run will start at time time {start_time}; cur_time is {time.time()}.")
		
		the_dict = {"start_time": start_time,
			        "start_time_long": str(datetime.datetime.now()+datetime.timedelta(0,start_delta))
				   }
		self.instance_info = the_dict
		with open(f"{self.scenario_dir}/netem/globals/instance_info.json", "w") as fp:
			fp.write(json.dumps(self.instance_info, indent=2))

		with open(f"{self.scenario_dir}/netem/globals/container_info.json", "w") as fp:
			fp.write(json.dumps(self.container_info, indent=2))

		#
		# Start command_processing threads.  Need to ensure that the various node_lists
		# here cover (without duplication) all the nodes
		#
		logger.info(json.dumps(the_dict, indent=2))
		for c in self.scenario_dict["node_configs"]:
			t = self.cmd_processing_thread( name=f"cmd_processing_thread for {c}",
											kwargs={'scenario':self,
										           'node_list':[c],
										           'command_list':self.scenario_dict["commands"]})
			t.start()
			self.command_threads += [t]

		#
		# Start the link characteristic processing threads.  Need to ensure that the various
		# (src,dst) lists here cover (without duplication) all of the links.
		#
		# Initial take: one link management thread per link.
		#
		logger.info("Starting link_management_thread(s).")
		link_pairs = self.topology.list_link_pairs()
		for e in link_pairs:
			logger.info(f"Instantiating link management thread for {e}")
			node_pairs = [e]
			t = self.link_management_thread(name=f"link_management_thread for {node_pairs}",
											kwargs={'scenario': self,
													'node_pairs': node_pairs,
													'iface_info': None,
													'topology_df': self.topology.df})
			t.start()
		self.link_management_threads += [t]

		#
		# Wait for the start time.  Note that commands may be executing in
		# the interim.
		#
		WAIT_TIME_THRESHOLD = 0.002
		while time.time()<the_dict["start_time"]:
			time_needed = max(the_dict["start_time"]-time.time(), 0)
			logger.info(f"Waiting to start {start_time-time.time():.2f}...")
			if time_needed>1 and (time_needed-int(time_needed)>WAIT_TIME_THRESHOLD):
				time.sleep(time_needed-int(time_needed)-WAIT_TIME_THRESHOLD)
			else:
				time.sleep(min(1, time_needed))
		logger.info("Time starts.")
		self.statsd_client.gauge("netem_event", 1, tags={"event": "t=0"})

		#
		# Wait for everything to be done
		#
		next_print = time.time()+5
		while (time.time()-start_time)<self.topology.df["time"].max():
			cur_time = time.time()
			if cur_time>=next_print:
				logger.info(f"abs_time: {cur_time}  rel_time: {self.reltime.get_reltime():.6f} -- waiting for {self.topology.df['time'].max()}")
				next_print += 5
			time_needed = next_print-cur_time
			time.sleep(time_needed+WAIT_TIME_THRESHOLD)
		
		logger.info(f"Joining cmd_processing threads ({len(self.command_threads)})")
		self.join_threads(self.command_threads)

		logger.info(f"Joining link processing threads ({len(self.link_management_threads)})")
		self.join_threads(self.link_management_threads)


	def join_threads(self, thread_list):
		for t in thread_list:
			logger.info(f"    {t.name}")
		for t in self.command_threads:
			if t.is_alive():
				while t.is_alive():
					t_status = t.status()
					logger.info(f"Joining {t.name} with {len(t_status['active_threads'])} threads")
					t.join(5)
			else:
				print(f"Joined {t.name}")



if __name__=="__main__":

	if os.getuid()!=0:
		logger.warning("You probably want to run this as root in order to be able to modify link parameters.")
		logger.warning("Abort or Continue (A/c)")
		res = str(input())
		if len(res)==0 or res[0]=="C" or res[0]=="c":
			logger.warning("Continuing as non-root user.")
		else:
			logger.fatal("Canceling due to not being root.")
			sys.exit(0)

	SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))

	logger = netem_logging.get_sublogger("scenario")
	
	parser = argparse.ArgumentParser()
	parser.add_argument("scenario_file", default=None)
	parser.add_argument("--start_on_minute", action="store_true", default=False)
	parser.add_argument("--leave_containers", "-l", default=False, action="store_true")
	args = parser.parse_args()

	if args.scenario_file==None:
		logger.fatal("Must provide a scenario file (JSON).")
		sys.exit(-1)

	scenario_dir = os.path.dirname(os.path.realpath(args.scenario_file))

	netem_logging.do_logging_config(scenario_dir)
	# if os.path.exists(f"{scenario_dir}/logging.conf"):
	# 	logging.config.fileConfig(f'{scenario_dir}/logging.conf')
	# 	logging.info(f"Using logging.conf from {scenario_dir}")
	# else:
	# 	logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')
	# 	logging.info(f"Using logging.conf from {SOURCE_DIR}")

	logger.info(f"netem begins")

	logger.info(f"Scenario file is {args.scenario_file}")
	logger.info(f"Leave_containers is {args.leave_containers}")

	foo = netem_scenario(args=vars(args))
	
	foo.load_scenario(args.scenario_file)

	foo.instantiate_docker_infrastructure()

	# Flush all the loggers, in particular the file logger.
	[h.flush() for h in logger.handlers]

	logger.debug(json.dumps(foo.container_info, indent=2))

	foo.run()

	time.sleep(10)


	# Unless asked to leave the infrastructure lying around, remove the containers
	# and networks.
	if not args.leave_containers:
		logger.info("Cleaning up containers now.")
		clean_containers.cleanup_all()

	# TODO: Really should go through all the nodes' mounts and catch those; this
	#       ASSUMES that they're all under the scenario directory.
	netem_utilities.reset_ownership(scenario_dir)

	logger.info(f"netem ends")


