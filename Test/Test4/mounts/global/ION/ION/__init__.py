#!/usr/bin/env python3

import sys
import os
import shutil
import logging

logging.basicConfig(filename='ion_config_tool.log', encoding='utf-8', level=logging.DEBUG)

logger = logging.getLogger("ion_config_tool")

class induct(object):
    def __init__(self, protocol):
        self.protocol = protocol
    
    def __repr__(self):
        return(f"induct({self.protocol})")

    def __str__(self):
        return(f"induct({self.protocol})")


class outduct(object):
    def __init__(self, protocol, dest_node_number, dest_identifier=None, dest_name=None):
        self.protocol = protocol
        self.dest_node_number = dest_node_number
        if dest_identifier==None:
            self.dest_identifier = dest_node_number     # e.g. LTP engine ID
        else:
            self.dest_identifier = dest_identifier     # IP address
        self.dest_name = dest_name

    def __str__(self):
        return(f"outduct({self.protocol} {self.dest_node_number} {self.dest_identifier} {self.dest_name})")

    def __repr__(self):
        return(f"outduct({self.protocol} {self.dest_node_number} {self.dest_identifier} {self.dest_name})")

class ion_node(object):
    from ._ionconfig import write_ionconfig
    from ._bprc      import write_bprc
    from ._ipnrc     import write_ipnrc
    from ._ionrc     import write_ionrc
    from ._ipnrc     import write_ipnrc
    from ._ltprc     import write_ltprc

    def __init__(self, node_name, node_number, num_services=10, output_dir=None):
        logger.info("=================START==============")
        self.node_name = node_name
        self.node_number = node_number
        self.num_services = num_services
        self.inducts = []
        self.outducts = []
        self.protocols = []
        self.induct_peers = []

        if output_dir==None:
            self.output_directory = f"ION_{self.node_name}"
        else:
            self.output_directory = f"{output_dir}/ION_{self.node_name}"
        logger.info(f"dir for ION configs for {self.node_name} is {self.output_directory}")

    def add_induct(self, protocol):
        self.inducts += [induct(protocol)]
        if protocol not in self.protocols:
            self.protocols += [protocol]
    
    def add_induct_peer(self, peer_node_number):
        if peer_node_number not in self.induct_peers:
            self.induct_peers += [peer_node_number]

    def add_outduct(self, protocol, dest_node_number, dest_identifier=None, dest_name=None):
        if dest_name==None:
            logger.warning("Adding outduct without dest node name.")
            logger.info(f"dest_node_number: {dest_node_number}")
            sys.exit(0)
        self.outducts += [outduct(protocol, dest_node_number, dest_identifier, dest_name)]
        if protocol not in self.protocols:
            self.protocols += [protocol]

    def write_configs(self, base_dir="."):
        # shutil.rmtree(self.output_directory, ignore_errors=True)
        logger.info(f"Writing configs for {self.node_name} to {self.output_directory}")
        os.makedirs(self.output_directory, exist_ok=True)
        self.write_ion_env()
        self.write_ionconfig()
        self.write_bprc()
        self.write_ionrc()
        self.write_ionsecrc()
        self.write_ipnrc()
        self.write_ltprc()
        # self.write_self_contacts()
        self.write_other_contacts()

    def write_ionsecrc(self):
        the_filename = f"{self.output_directory}/{self.node_name}.ionsecrc"
        if os.path.exists(the_filename):
            os.remove(the_filename)

        with open(the_filename, "w") as fp:
            fp.write("1\n")

    def write_ion_env(self):
        the_filename = f"{self.output_directory}/ion.env"
        if os.path.exists(the_filename):
            os.remove(the_filename)
        with open(the_filename, "w") as fp:
            fp.write(f'NODE_NAME="{self.node_name}"\n')
            fp.write(f'"NODE_NUMBER={self.node_number}"\n')
    
    def write_self_contacts(self):
        the_filename = f"{self.output_directory}/self_contacts.ionrc"
        if os.path.exists(the_filename):
            os.remove(the_filename)
        with open(the_filename, "w") as fp:
            fp.write(f"# 'loopback' contact\n")
            fp.write(f"# contact +<rel_start> +<rel_length> <src> <dst> <rate_bps>\n")
            fp.write(f"a contact +0 +1000000 {self.node_number} {self.node_number} 1000000\n")
            fp.write(f"# range +<rel_start> +<rel_length> <src> <dst> <owlt_s>\n")
            fp.write(f"a range +0 +1000000 {self.node_number} {self.node_number} 1\n\n")

    def write_other_contacts(self):
        the_filename = f"{self.output_directory}/outbound_contacts.ionrc"
        if os.path.exists(the_filename):
            os.remove(the_filename)
        with open(the_filename, "w") as fp:
            # logger.info(f"Inbound contacts to ({self.node_name}, {self.node_number}) from peers: {self.induct_peers}")
            # fp.write(f"# Inbound contacts to ({self.node_name}, {self.node_number}) from peers: {self.induct_peers}\n")
            # for induct_from_node_number in self.induct_peers:
            #     fp.write(f"a contact +0 +1000000 {induct_from_node_number} {self.node_number} 1000000\n")
            #     fp.write(f"a range +0 +1000000 {induct_from_node_number} {self.node_number} 1\n")

            logger.info(f"Outbound contacts from ({self.node_name}, {self.node_number}) to peers: {[(outduct.dest_name, outduct.dest_node_number) for outduct in self.outducts]}")
            fp.write(f"# Outbound contacts from ({self.node_name}, {self.node_number}) to peers: {[(outduct.dest_name, outduct.dest_node_number) for outduct in self.outducts]}\n")
            for outduct in self.outducts:
                fp.write(f"# Outbound contact from node {self.node_number} to node ({outduct.dest_name, outduct.dest_node_number})\n")
                fp.write(f"a contact +0 +1000000 {self.node_number} {outduct.dest_node_number} 1000000\n")
                fp.write(f"a range +0 +1000000 {self.node_number} {outduct.dest_node_number} 1\n")
