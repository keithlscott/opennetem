====================
Scenario File format
====================

The overall format of a scenario file is ::

   {
       "Scenario": "test1",
       "Metadata": {},
       "start_delta": 15,                #(minimum # of seconds between network instantiation and time 0 of emulation)
       "start_on_minute": true,          #(if true, cause time 0 of emulation to fall on a minute boundary)
       "topology_filename": "test_topo.csv",
       "topology_sheetname": "Sheet1",   #(only needed if the topo file is .xlsx)
       "networks": {
           <see below>
       },
       "node_configs": {
           <see below>
       },
       "commands": [
           <see below>
       ]
   }

When using an ``.xlsx`` file to specify the time-variant network dynamics, the scenario
file must include a ``topology_sheetname`` entry.



networks
=========
A dictionary of networks keyed by (arbitrary) network name that contain values
for "network" (a dotted quad with netmask) and "gateway" (dotted quad) ::

   "ab": {
      "network": "10.44.3.0/24",
      "gateway": "10.44.3.254"
   },

Netem will generate docker networks corresponding to the networks in the "networks"
section, with "netem\_" prepended to the network names so that the networks managed
by netem are easily distinguishable.



node_configs
============
A dictionary of nodes keyed by node name with information about the node. ::

   "node_a": {
      "container_image": "netem1",
      "ipv4_addresses": [["ab", "10.44.3.1"], ["ac", "10.46.7.1"]]
      "mounts": [["mounts/node_a", "/netem/mounts/node_a"]],
      "working_dir": "/netem/mounts/node_a"
    },

The ``ipv4_addresses`` list allows fine-grained control over the addresses of the node's
interfaces on the networks defined in the ``networks`` section.  I believe that the
interface names for these addresses will start at eth2 but I don't do anything to
ensure that.

``mounts`` is a list of tuples to bind-mount into the container.  The first element
of the tuple is the host directory (relative to the directory containing the scenario
file) and the second element is the location in the container at which to mount the
directory.

``working_dir`` sets the working directory for the container (the initial directory
when you use ``docker exec -it netem_<NODE_NAME> bash`` to get a shell in the container).

The container names are the same as the node names with ``netem_``  prepended to them
so that the containers managed by netem are easily distinguishable.



Running Commands in Containers
===============================
If the scenario.json file has a "commands" section formatted as: ::

  "commands": [
      {"time": t1, "nodes": ["*"],                "command": "<linux command>"},
      {"time": t2, "nodes": ["node_a"],           "command": "<linux command>"},
      {"time": t3, "nodes": ["node_a", "node_b"], "command": "<linux command>"}
  ]

then the commands will be run in the specified nodes at the specified times.  Note that the
specification of nodes is passed directly to the python docker container's list function
as a ``filter={"name": <>}`` argument, allowing a given command to be run on multiple nodes.

Internally the commands are wrapped in ::

"""/bin/bash -c '<linux command>'"""

so that shell functions (e.g. pipes, redirection) have a chance of working.

Threads are spawned to manage commands for collections of nodes (currently one thread per node).
Multiple commands may be executed at the same time, and a node may have any number of commands
running concurrently.

The strings ``NETEM_NODE_NAME`` and ``NETEM_START_TIME`` in commands are replaced with the
node name and the start time (in seconds since epoch).  netem attempts to always start
emulations on a second boundary.


Command Examples
----------------
The following command runs ``echo `date + '%s.%N'``` into the ``/netem/mounts/<NODE_NAME>`` directory on each
node.  The ``/netem/mounts/<NODE_NAME>`` directories were individually specified in the various
nodes' ``node_configs`` in the scenario file.::

``{"time": 15, "nodes": ["*"],      "command": "echo `date +'%s.%N'` > /netem/mounts/NETEM_NODE_NAME/t_15"}``

After running, the following are left in the various nodes' directories: ::

    % find .  -name "t_15" | xargs -i sh -c 'ls -l {} && cat {}'
    -rw-r--r-- 1 kscott kscott 21 feb 15 14:36 ./mounts/node_a/t_15
    1708004175.055128297
    -rw-r--r-- 1 kscott kscott 21 feb 15 14:36 ./mounts/node_c/t_15
    1708004175.104012575
    -rw-r--r-- 1 kscott kscott 21 feb 15 14:36 ./mounts/node_b/t_15
    1708004175.105347288

Note that even though the commands where all scheduled to run at the same time and were executed from
different threads within the netem context, they still ended up executing as much as 50ms apart.

----

The following json snippet runs a command at time t=-5 (i.e. the command starts running
5 seconds before 0-time in the emulation).  It first sets the environment variable ``foo``
to the emulation start time by reading it out of ``/netem/globals/instance_info.json``.
It then starts a ``ping`` to ``10.44.3.2`` and pipes the output through a while loop that
calculates the relative time of the RECEIPT of the ping and prepends a receive-time
timestamp and the relative receive time to the rest of the output from ping.::

``{"time": -5, "nodes": ["node_a"], "command": "export foo=`cat /netem/globals/instance_info.json | jq '.start_time'`; ping -4 -c 60 10.44.3.2 | while read pong; do reltime=$(expr `date +'%s'` - $foo); echo `date +'%Y-%m-%d_%H:%M:%S,%N'` $reltime $pong; done > /netem/mounts/node_a/a_to_b_ping.txt"}``

Sample output from the command is::

    2024-02-15_12:48:55,133861600 -5 PING 10.44.3.2 (10.44.3.2) 56(84) bytes of data.
    2024-02-15_12:48:55,136141578 -5 64 bytes from 10.44.3.2: icmp_seq=1 ttl=64 time=0.062 ms
    2024-02-15_12:48:56,152640891 -4 64 bytes from 10.44.3.2: icmp_seq=2 ttl=64 time=0.036 ms
    2024-02-15_12:48:57,182217026 -3 64 bytes from 10.44.3.2: icmp_seq=3 ttl=64 time=0.035 ms
    2024-02-15_12:48:58,200773210 -2 64 bytes from 10.44.3.2: icmp_seq=4 ttl=64 time=0.025 ms
    2024-02-15_12:48:59,220635977 -1 64 bytes from 10.44.3.2: icmp_seq=5 ttl=64 time=0.026 ms
    2024-02-15_12:49:00,257698934 0 64 bytes from 10.44.3.2: icmp_seq=6 ttl=64 time=13.1 ms
    2024-02-15_12:49:01,258898916 1 64 bytes from 10.44.3.2: icmp_seq=7 ttl=64 time=13.1 ms
    2024-02-15_12:49:02,260010066 2 64 bytes from 10.44.3.2: icmp_seq=8 ttl=64 time=13.1 ms
    2024-02-15_12:49:03,260951320 3 64 bytes from 10.44.3.2: icmp_seq=9 ttl=64 time=13.1 ms
    2024-02-15_12:49:04,261569884 4 64 bytes from 10.44.3.2: icmp_seq=10 ttl=64 time=13.1 ms

----

The following command uses the ``ping_monitor.py`` script included in the /netem/netem_tools directory
that's mounted into each container to record ping times to the influxdb server that is part
of the monitor stack.  ``ping_monitor.py`` differs from the previous ping example in that it
logs the round-trip time using the time the ping was launched instead of the time it was received
(by subtracting the RTT from the receive time).::

``{"time": -3, "nodes": ["node_a"], "command": "/netem/netem_tools/ping_monitor.py --use-ipv4 --target 10.44.3.2 --count=10000 --influxdb --verbose &> /netem/mounts/node_a/ping_monitor.out"}``

Output is also logged to ``node_a``'s directory in the ``ping_monitor.out`` file::

    cmd is: ['ping', '-c', '10000', '-4', '10.44.3.2']
    {'receive_time': '2024-02-15 13:35:57.282223', 'receive_time_epoch': '1708004157.2822309', 'bytes_received': 64, 'payload_size': -1, 'sequence': 1, 'ttl': 64, 'time': 0.049, 'time_units': 'ms', 'transmit_time_abs': 1708004157.2821817, 'transmit_time_abs_str': '2024-02-15 13:35:57.282182', 'transmit_time_rel': -2.7177954962005617, 'source': 'node_a', 'target': '10.44.3.2'}
    {'receive_time': '2024-02-15 13:35:58.284084', 'receive_time_epoch': '1708004158.284097',  'bytes_received': 64, 'payload_size': -1, 'sequence': 2, 'ttl': 64, 'time': 0.037, 'time_units': 'ms', 'transmit_time_abs': 1708004158.2840600, 'transmit_time_abs_str': '2024-02-15 13:35:58.284060', 'transmit_time_rel': -1.7159016583557130, 'source': 'node_a', 'target': '10.44.3.2'}
    {'receive_time': '2024-02-15 13:35:59.314582', 'receive_time_epoch': '1708004159.3145936', 'bytes_received': 64, 'payload_size': -1, 'sequence': 3, 'ttl': 64, 'time': 0.033, 'time_units': 'ms', 'transmit_time_abs': 1708004159.3145607, 'transmit_time_abs_str': '2024-02-15 13:35:59.314561', 'transmit_time_rel': -0.6854024915771484, 'source': 'node_a', 'target': '10.44.3.2'}
