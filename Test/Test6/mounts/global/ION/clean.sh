#!/bin/bash

rm -f ion_config_tool.log

rm -rf ION_node_a ION_node_b ION_node_c

rm -f mounts/node_a/node_a.*
rm -f mounts/node_a/ion.env
rm -f mounts/node_a/self_contacts.ionrc

rm -f mounts/node_b/node_b.*
rm -f mounts/node_b/ion.env
rm -f mounts/node_b/self_contacts.ionrc

rm -f mounts/node_c/node_c.*
rm -f mounts/node_c/ion.env
rm -f mounts/node_c/self_contacts.ionrc
