Test1
========

This test exercises the basic capabilities of the emulator:
  - Instantiating nodes with a given topology
  - Running commands in the node containers at specific times
      - Replacing NETEM_NODE_NAME with the node name in commands
  - Dynamically controlling the link characteristics among the nodes
  - Using in-container scripts to monitor and report the dynamic network conditions
    to the monitoring framework via influxdb and Grafana

Nodes in this test:
  - node_a
  - node_b
  - node_c

with node_a connected to node b,  node_b connected to node_a and node_c, and node_c connected to node_b

Note that there is no IP routing in this scenario; routes are NOT instantiated from node_a to node_c and vice-versa.

The Test1 scenario file is::

    {   "Scenario": "test1",
        "Metadata": {},
        "start_delta": 15,
        "topology_filename": "test1_topo.xlsx",
            "topology_sheetname": "Sheet1",
            "networks": {
            "ab": {
                "network": "10.44.3.0/24",
                "gateway": "10.44.3.254"
            },
            "bc": {
                "network": "10.45.7.0/24",
                "gateway": "10.45.7.254"
            },
            "ac": {
                "network": "10.46.7.0/24",
                "gateway": "10.46.7.254"
            }
        },
        "node_configs": {
            "__global": {
                "mounts": [["mounts/global", "/netem/mounts/global"]]
            },
            "node_a": {
                "container_image": "netem1",
                "ipv4_addresses": [["ab", "10.44.3.1"], ["ac", "10.46.7.1"]],
                "mounts": [["mounts/node_a", "/netem/mounts/node_a"]],
                "working_dir": "/netsim/mounts/node_a"
            },
            "node_b": {
                "container_image": "netem1",
                "ipv4_addresses": [["ab", "10.44.3.2"], ["bc", "10.45.7.1"]],
                "mounts": [["mounts/node_b", "/netem/mounts/node_b"]],
                "working_dir": "/netsim/mounts/node_b"
            },
            "node_c": {
                "container_image": "netem1",
                "ipv4_addresses": [["bc", "10.45.7.2"], ["ac", "10.46.7.2"]],
                "mounts": [["mounts/node_b", "/netem/mounts/node_b"]],
                "working_dir": "/netsim/mounts/node_c"
            }
        },
        "commands": [
            {"time": -5, "nodes": ["node_a"], "command": "export foo=`cat /netem/globals/instance_info.json | jq '.start_time'`; ping -4 -c 60 10.44.3.2 | while read pong; do reltime=$(expr `date +'%s'` - $foo); echo `date +'%Y-%m-%d_%H:%M:%S,%N'` $reltime $pong; done > /netem/mounts/node_a/a_to_b_ping.txt"},
            {"time": -5, "nodes": ["node_b"], "command": "echo `date +'%s.%N'` > /netem/mounts/NETEM_NODE_NAME/b_at_minus_5"},
            {"time": -3, "nodes": ["node_a"], "command": "/netem/netem_tools/ping_monitor.py --use-ipv4 --target 10.44.3.2 --count=10000 --influxdb --verbose &> /netem/mounts/node_a/ping_monitor.out"},
            {"time": -2, "nodes": ["node_a"], "command": "tcpdump -nn -l -i any icmp -w /netem/mounts/node_a/ping_monitor.pcap"},
            {"time": 15, "nodes": ["*"],      "command": "echo `date +'%s.%N'` > /netem/mounts/NETEM_NODE_NAME/t_15"},
            {"time": 30, "nodes": ["node_a"], "command": "ls -lR /etc > /netem/mounts/NETEM_NODE_NAME/ls_1.txt"},
            {"time": 45, "nodes": ["node_a", "node_b"], "command": "ls -lR /netem > /netem/mounts/NETEM_NODE_NAME/ls_2.txt"}
        ]
    }


The dynamic network connectivity is as follows:

.. list-table:: Dynamic Network Connectivity for Test1
   :widths: 25 25 25 25 25 25
   :header-rows: 1

   * - Time
     - Source
     - Dest
     - Delay
     - Loss
     - Data Rate
   * - 0
     - node_a
     - node_b
     - 0s
     - 0
     - 100kbit
   * - 
     - node_b
     - node_a
     - 0s
     - 0
     - 150kbit
   * - 30
     - node_a
     - node_b
     - 3s
     - 0
     - 150kbit
   * -
     - node_b
     - node_a
     - 4s
     - 0
     - 100kbit
   * -
     -
     - node_c
     - 2s
     - 0
     - 50kbit
   * - 
     - node_c
     - node_b
     - 1s
     - 0
     - 100kbit
   * - 60
     - node_a
     - node_b
     - 
     - 
     - 
   * -
     - node_b
     - node_a
     - 
     - 
     - 
   * -
     - node_b
     - node_c
     - 
     - 
     - 
   * - 
     - node_c
     - node_b
     - 
     -
     -
   * - 90
     - node_a
     - node_b
     - 500ms
     - 0
     - 100kbit
   * - 
     - node_b
     - node_a
     - 2s
     - 0
     - 150kbit
   * - 
     - node_b
     - node_c
     - 1400ms
     - 0
     - 200kbit
   * - 
     - node_c
     - node_a
     - 1s
     - 0
     - 100kbit
   * - 120
     - node_a
     - node_b
     - 0.5s
     - 0
     - 100kbit
   * - 
     - node_b
     - node_a
     - 0.5s
     - 0
     - 150kbit



So that if we ping from node_a to node_b we would expect the RTTs to be

.. list-table:: Expected a-b Round-Trip-Time for Test1
   :widths: 25 25 25 25 25
   :header-rows: 1

   * - 0-30s
     - 30-60s
     - 60-90s
     - 90-120s
     - 120-150s
   * - 0
     - 7s
     - Disconnected
     - 2.5s
     - 1s

This is shown in the following, taken from the ping_monitor.py script that exports data to influxdb for graphing with grafana.

.. image:: Test1_latency.png
  :width: 100%
  :alt: Alternative text
