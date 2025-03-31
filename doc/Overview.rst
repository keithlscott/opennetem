============
Overview
============

opennetem is a package for emulating networks using docker containers.  Each container
emulates a node in the network, and docker networks (ethernet bridges) connect
the nodes.  In this sense it is similar to the `Kathará <https://www.kathara.org/>`_.
or `Mininet <http://mininet.org>`_. with
`Containernet <https://containernet.github.io/>`_.  packages.

opennetem was designed to help emulate a special class of networks that have **time-variant
link characteristics / topologies**.  Examples of such networks include space networks (
either constellations of spacecraft, networks of spacecraft around the Earth and/or
other planets like Mars, or even single missions whose connectivity to the ground
is not continuous / homogeneous) and some terrestrial networks (sensor networks, networks
deployed in remote areas, underwater networks).  Thus instead of defining a single network topology,
opennetem allows the specification of time-tagged link characteristics.

The opennetem package uses the linux advanced routing and traffic control (`tc`) netem queueing
discipline to impose link characteristics (delay, data rate limitations, and packet
loss).  It does this by applying netem qdiscs to the veth interfaces on the docker
host that connect to the containers.  This allows the containers (should they so
desire) to apply their own queueing disciplines to their links.  While it's possible
to chain queueing disciplines together so that container-specific ones could be 
applied before the netem qdisc, there are issues with this in practice, so the netem
package imposes the tc netem qdiscs at the host level rather than applying them to
the interfaces inside the containers.  This also reduces the in-container complexity
(though not necessarily the overall load on the system).

Scenario Specification
======================
opennetem uses json files to specify scenarios.  The top-level scenario file contains

  - The scenario name
  - The (possibly time-variant) scenario topology or a reference to another file that
    contains the topology
  - Information about the configurations of the various nodes in the scenario e.g.:

    - What docker container image to use for the node
    - The networks to which the node is connected along with symbolic names that can be
      used in other parts of the script
    - A list of bind mounts to use for the node; these associate directories on the host with
      directories inside the node and are used to pass configuration information to the nodes
      and to allow nodes to log information that
      persists beyond shutting down the docker container.

  - A list of commands to be executed at specified times, on specific nodes.  Commands can be
    executed on individual nodes or wildcarded to execute on all nodes.

The :ref:`Examples::Test1<Test1>` section of the documentation contains the scenario file for a simple test.

Opennetem will stop and remove the containers once the emulation ends (after the last command is run).
If you'd prefer to use Opennetem
to set up a network that you want to leave up for experimentation, simply add a command to the command list
(e.g. ``ls``) that runs a very long time in the future.


Node-Based Data Collection
==========================
The simplest form of data collection is for nodes to write into directories that are bind-mounted
from the host.  Data written to such directories will persist once the scenario ends.

The Monitor Stack
=================
opennetem comes with a monitoring stack with a couple of time-series databases and Grafana for
visualization.  Pre-packaged docker volumes contain configuration information to get the
stack running.  More information about the monitoring stack is availble in the
:ref:`Monitoring` section.
