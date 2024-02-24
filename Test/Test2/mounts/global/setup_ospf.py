#!/usr/bin/env python3

import ipaddress
import subprocess
import json

def get_addr_of_interface(interface_info, interface_name):
	for interface in interface_info:
		if "ifname" not in interface:
			continue
		if interface["label"]==interface_name:
			return(interface["local"])

def main():
	print(f"This is main.")

	#
	# Get interface info
	#
	ret = subprocess.run("ip --json address show".split(), capture_output=True)
	# print(f"{ret.stdout}")
	info = json.loads(ret.stdout)

	cmd = "config t\nrouter ospf\n\npassive-interface dock\npassive-interface mon"
	subprocess.run(["vtysh", "-c", cmd])

	router_id = None

	#
	# Turn on ospf on each of the router's interfaces (except lo, dock, and mon)
	#
	ignored_interfaces = ["lo", "dock", "mon"]

	for interface in info:
		if "ifname" not in interface or interface["ifname"] in ignored_interfaces:
			continue
		for addr_info in interface['addr_info']:

			# Default router id is the first address
			# we find.
			if addr_info["family"]!="inet":
				continue
			if router_id==None:
				router_id = addr_info["local"]

			the_iface_with_mask=f"{addr_info['local']}/{addr_info['prefixlen']}"
			the_network = ipaddress.ip_network(the_iface_with_mask, strict=False)
			cmd = f"config t\nrouter ospf\nnetwork {the_network} area 0"
			ret = subprocess.run(["vtysh", "-c", cmd])
			# print(f"Output of config command {cmd}:\n{ret.stdout}")

	# Set the router ID
	cmd = f"config t\nrouter ospf\nospf router-id {router_id}"
	subprocess.run(["vtysh", "-c", cmd])

	return

if __name__=="__main__":
	main()

