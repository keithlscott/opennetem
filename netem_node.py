#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import shutil
import docker
import os
import netem_logging

logger = netem_logging.get_sublogger("node")

class netem_node(object):
    # node_config is the node's entry from the node_configs
    # portion of the scenario config file
    def __init__(self, scenario, node_name, node_config, global_config):
        self.scenario = scenario
        self.client = docker.from_env()
        self.node_name = node_name
        self.node_config = node_config.copy()
        self.global_config = global_config
        self.container = None
        logger.info(f"Creating node from {node_config}")
        self.create_container()
        return
    

    def rename_interface(self, fromName, toName):
        self.container.exec_run(f"ip link set dev {fromName} down")
        self.container.exec_run(f"ip link set dev {fromName} name {toName}")
        self.container.exec_run(f"ip link set dev {toName} up")


    def create_container(self):
        my_host_dir = f"{self.scenario.scenario_dir}/netem/{self.node_name}"

        try:
            os.makedirs(my_host_dir, mode = 0o777, exist_ok=True)
            mounts = [docker.types.Mount(f"/netem/netem_tools",  f"{self.scenario.install_dir}/netem_tools", type="bind", read_only=True),
                      docker.types.Mount(f"/netem/globals", f"{self.scenario.scenario_dir}/netem/globals", type="bind", read_only=True),
                      docker.types.Mount(f"/netem/node", my_host_dir, type="bind")]
            
            # This adds mount points from both the node_config and global_config
            # sections of the 'node_configs' section of the scenario file.
            working_dir = "/"
            for config_source in [self.node_config, self.global_config]:
                # Add in any node-specific mounts from the scenario file
                if "mounts" in config_source:
                    for m in config_source["mounts"]:
                        src_dir = self.scenario.scenario_dir+"/"+m[0]
                        if not os.path.exists(src_dir):
                            os.makedirs(src_dir, exist_ok=True)
                        mounts += [docker.types.Mount(m[1], src_dir, type="bind")]
                if "working_dir" in config_source:
                    working_dir = config_source["working_dir"]

            #
            # Add any capabilities listed in the "capabilities" line of the node config
            #
            capability_list = ["NET_ADMIN"]
            if "capabilities" in self.node_config:
                for cap in self.node_config["capabilities"]:
                    if cap not in capability_list:
                        capability_list += [cap]
            
            self.container = self.client.containers.create(
                self.node_config["container_image"],
                # command="tail -f /dev/null",
                # name="netem_"+self.node_name,          # Container name gets netem_ prepended to it.
                name=self.node_name,          # Container name gets netem_ prepended to it.
                privileged=True,
                cap_add=["NET_ADMIN"],
                hostname=self.node_name,
                labels={"netem_node": "True"},
                mounts=mounts,
                working_dir=working_dir,
                detach=True
            )

        except docker.errors.APIError as e:
            logger.warning(f"Error creating container: {e}")
            return None

