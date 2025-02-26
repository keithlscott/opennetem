===============================
Container Directories and Files
===============================
Each container gets directories from the working directory bind-mounted into it.  A ``netem``
directory will be created on the host with directories underneath it for use by the
containers.

/netem/globals
==============

``globals`` (read-only directory; mounted at ``/netem/globals``)
   Read-only directory containing information from the netem controller, such as the
   start time of the simulation (to synchronize the various containers' notions of time)

/netem/netem_tools
------------------
``netem_tools`` is a read-only directory; mounted at ``/netem/netem_tools``.  It contains
applications and utilities designed to be run inside containers.


ping-monitor
^^^^^^^^^^^^^
``ping_monitor.py`` -- ping_monitor.py monitors
the output of the ping command.  It augments the ping output with additional information
such as the transmit time and optionally logs it to the influxdb database in the
netem monitoring stack.::

   usage: ping_monitor.py [-h] [--target TARGET] [--interval INTERVAL] [--count COUNT] [--use-ipv4] [--influxdb] [--verbose]

   options:
   -h, --help           show this help message and exit
   --target TARGET
   --interval INTERVAL
   --count COUNT
   --use-ipv4
   --influxdb           Write to influxDB.
   --verbose

with ``--verbose`` ``ping_monitor.py`` will output lines of the form::

   {'receive_time': '2024-02-15 13:35:59.314582',
    'receive_time_epoch': '1708004159.3145936',
    'bytes_received': 64,
    'payload_size': -1,
    'sequence': 3,
    'ttl': 64,
    'time': 0.033,
    'time_units': 'ms',
    'transmit_time_abs': 1708004159.3145607,
    'transmit_time_abs_str': '2024-02-15 13:35:59.314561',
    'transmit_time_rel': -0.6854024915771484,
    'source': 'node_a',
    'target': '10.44.3.2'
    }
   {'receive_time':
    '2024-02-15 13:36:00.355652',
    'receive_time_epoch': '1708004160.3556645',
    'bytes_received': 64,
    'payload_size': -1,
    'sequence': 4, 'ttl': 64, 'time': 13.1,
    'time_units': 'ms', 'transmit_time_abs': 1708004160.3425646,
    'transmit_time_abs_str': '2024-02-15 13:36:00.342565',
    'transmit_time_rel': 0.3426019233703613,
    'source': 'node_a',
    'target': '10.44.3.2'
    }
   {'receive_time': '2024-02-15 13:36:01.356791',
    'receive_time_epoch': '1708004161.3568044',
    'bytes_received': 64,
    'payload_size': -1,
    'sequence': 5,
    'ttl': 64,
    'time': 13.1,
    'time_units': 'ms',
    'transmit_time_abs': 1708004161.3437045,
    'transmit_time_abs_str': '2024-02-15 13:36:01.343704',
    'transmit_time_rel': 1.3437398952484132,
    'source': 'node_a',
    'target': '10.44.3.2'
    }
   {'receive_time': '2024-02-15 13:36:02.357922',
    'receive_time_epoch': '1708004162.3579352',
    'bytes_received': 64,
    'payload_size': -1,
    'sequence': 6,
    'ttl': 64,
    'time': 13.1,
    'time_units': 'ms',
    'transmit_time_abs': 1708004162.3448353,
    'transmit_time_abs_str': '2024-02-15 13:36:02.344835',
    'transmit_time_rel': 2.3448721450805663,
    'source': 'node_a',
    'target': '10.44.3.2'
    }
   {'receive_time': '2024-02-15 13:36:03.359081',
    'receive_time_epoch': '1708004163.3590965',
    'bytes_received': 64,
    'payload_size': -1,
    'sequence': 7,
    'ttl': 64,
    'time': 13.1,
    'time_units': 'ms',
    'transmit_time_abs': 1708004163.3459966,
    'transmit_time_abs_str': '2024-02-15 13:36:03.345997',
    'transmit_time_rel': 3.3460439723968505,
    'source': 'node_a',
    'target': '10.44.3.2'
    }

where each of the dictionaries above is entirely on one line.

set_static_arp
^^^^^^^^^^^^^^
The ``set_static_arp.py`` script can be invoked (generally in the `commands` section
of a scenario file) to set static arp entries in the nodes.  **NB** that at least when using
the frr container to implement OSPF routing, you need to wait a while before
invoking ``set_static_arp.py``, something on the order of 30--40 seconds.  This may
be an interaction with frr's ospf or something else, I haven't tracked it down yet.

``set_static_arp`` is intended to be invoked on a node (e.g. node_a) and
takes a node name and a network name as arguments (e.g. node_b, ab), and inserts
a static arp entry on node_a for node_b's interface(s) on network ab

The usage message for ``set_static_arp`` is::
   
   usage: set_static_arp.py [-h] [--node NODE] [--network NETWORK] [--verbose]

   options:
   -h, --help         show this help message and exit
   --node NODE
   --network NETWORK
   --verbose

reltime.sh
^^^^^^^^^^
``reltime.sh`` is a shell script that returns the current emulation time.
Use of reltime.sh is somewhat discouraged because it has to read the
emulation start time from /netem/globals every time it is invoked.
