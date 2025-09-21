Test4
========

Test4 uses `ion_config` elements in the scenario file to auto-configure
ION nodes.

Each `ion_config` element consists of:

`node_number` (optional): the ION node number.  If no node_number is provided
then the node will be auto-numbered starting at 400,000 (should really start
at the beginning of hte private number block).

`config_dir`: The directory into which the various ion config files should be
written.  The idea is that there will be a command in the commands section
to start ION from the configs in this directory.

`outducts`: A list of outduct pairs `[dest_node_name, CLA_name]`.  For now
opennetem assumes that auto-configured convergence layers are symmetric, so
`dest_node_name` should have an *outduct* with the same CLA pointed at
the current node.

For example, the `ion_config` blocks for the 3 nodes in Test4 are:

node_a:

.. code-block:: python

            "ion_config": {"node_number": 1,
                           "config_dir": "/netem/mounts/node_a/ION_CONFIGS",
	    		   "outducts": [["node_b", "ltp"]]}


node_b:

.. code-block:: python

            "ion_config": {"node_number": 2,
		           "outducts": [["node_a", "ltp"], ["node_c", "tcp"]],
                           "config_dir": "/netem/mounts/node_b/ION_CONFIGS"}

node_c:

.. code-block:: python

            "ion_config": {"outducts": [["node_b", "tcp"]],
		           "config_dir": "/netem/mounts/node_c/ION_CONFIGS"}
                           
Because node_c does not have a `node_number` element, it gets auto-numbered
as node 400000

Services
--------------

`bpecho` is auto-started on each of the nodes as service 1.




Connectivity
--------------------------

A set of fixed contacts is auto-generated, with the contacts for each node in `/netem/mounts/global/ION_contacts/NODE_NAME.ionrc`.  A command run ONCE
(e.g. on ONE of the nodes) should concatenate the various contact files together before passing them to ionadmin.


Commands
---------------

The commands for test4 are shown below.  The `/netem/mounts/global/ION/main.py` file reads the scenario file and generates the ion
configuration files.

.. code-block:: python

       "commands": [
        {"time":-15, "nodes": ["node_a"], "command": "rm -rf /netem/mounts/global/ION_contacts ; mkdir -p /netem/mounts/global/ION_contacts"},
        {"time":-14, "nodes": ["*"],      "command": "/netem/mounts/global/ION/main.py -w NETEM_NODE_NAME"},
        {"time":-13, "nodes": ["*"],      "command": "cp /netem/mounts/NETEM_NODE_NAME/ION_CONFIGS/outbound_contacts.ionrc /netem/mounts/global/ION_contacts/NETEM_NODE_NAME_contacts.ionrc"},
        {"time":-12, "nodes": ["node_a"], "command": "cat /netem/mounts/global/ION_contacts/node_*.ionrc > /netem/mounts/global/ION_contacts/all_contacts.ionrc"},
        {"time":-11, "nodes": ["*"],      "command": "cd /netem/mounts/NETEM_NODE_NAME/ION_CONFIGS ; source ion.env ; /netem/mounts/global/start_ion.sh >& /netem/mounts/NETEM_NODE_NAME/start_ion.out ; sleep 1"},
        {"time": 0,  "nodes": ["*"],      "command": "cd /netem/mounts/global && ionadmin /netem/mounts/global/ION_contacts/all_contacts.ionrc && sleep 1"},
        {"time": 20, "nodes": ["node_a"], "command": "nohup bpecho ipn:1.1 >& /netem/mounts/node_a/bpecho.out &"},
        {"time": 20, "nodes": ["node_b"], "command": "nohup bpecho ipn:2.1 >& /netem/mounts/node_b/bpecho.out &"},
        {"time": 20, "nodes": ["node_c"], "command": "nohup bpecho ipn:400000.1 >& /netem/mounts/node_c/bpecho.out &"}
    ]

