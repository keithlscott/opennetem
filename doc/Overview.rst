============
Overview
============

netem is a package for emulating networks using docker containers.  Each container
emulates a node in the network, and docker networks (ethernet bridges) connect
the nodes.  In this sense it is similar to the `Kathará <https://www.kathara.org/>`_.
or `Mininet <http://mininet.org>`_. with
`Containernet <https://containernet.github.io/>`_.  packages.

netem was designed to help emulate a special class of networks that have **time-variant** 
link characteristics / topologies.  Examples of such networks include space networks (
either constellations of spacecraft, networks of spacecraft around the Earth and/or
other planets like Mars, or even single missions whose connectivity to the ground
is not continuous / homogeneous) and some terrestrial networks (sensor networks, networks
deployed in remote areas, underwater networks).  Thus instead of defining a single network topology,
netem allows the specification of time-tagged link characteristics.

The netem package uses the linux advanced routing and traffic control (`tc`) netem queueing
discipline to impose link characteristics (delay, data rate limitations, and packet
loss).  It does this by applying netem qdiscs to the veth interfaces on the docker
host that connect to the containers.  This allows the containers (should they so
desire) to apply their own queueing disciplines to their links.  While it's possible
to chain queueing disciplines together so that container-specific ones could be 
applied before the netem qdisc, there are issues with this in practice, so the netem
package imposes the tc netem qdiscs at the host level rather than applying them to
the interfaces inside the containers.  This also reduces the in-container complexity
(though not necessarily the overall load on the system).

