# opennetem
A container-based network emulation system that accommodates time-variant topologies.

opennetem is a package for emulating networks using docker containers.  Each container
emulates a node in the network, and docker networks (ethernet bridges) connect
the nodes.  In this sense it is similar to the `Kathará <https://www.kathara.org/>`_.
or `Mininet <http://mininet.org>`_. with
`Containernet <https://containernet.github.io/>`_.  packages.

opennetem was designed to help emulate a special class of networks that have **time-variant**
link characteristics / topologies.  Examples of such networks include space networks (
either constellations of spacecraft, networks of spacecraft around the Earth and/or
other planets like Mars, or even single missions whose connectivity to the ground
is not continuous / homogeneous) and some terrestrial networks (sensor networks, networks
deployed in remote areas, underwater networks).  Thus instead of defining a single network topology,
opennetem allows the specification of time-tagged link characteristics.

The opennetem package uses the linux advanced routing and traffic control (`tc`) queueing
discipline to impose link characteristics (delay, data rate limitations, and packet
loss).  It does this by applying netem qdiscs to the veth interfaces on the docker
host that connect to the containers.  This allows the containers (should they so
desire) to apply their own queueing disciplines to their links.  While it's possible
to chain queueing disciplines together so that container-specific ones could be
applied before the netem qdisc, there are issues with this in practice, so the netem
package imposes the tc netem qdiscs at the host level rather than applying them to
the interfaces inside the containers.  This also reduces the in-container complexity
(though not necessarily the overall load on the system).


To install the right version of docker and docker-compose, follow the instructions
here (https://docs.docker.com/engine/install/ubuntu/) to add the docker repository
and then use *apt install docker-ce* and *apt install docker-compose-plugin*

Why: because different docker-compose versions will name containers differently
and we need them to have known names.

To build a python virtual environment in which to run opennetem, start with:

  pip install virualenv (if you don't already have virtualenv installed)

  virtualenv venv (to create a new python virtual environment called 'venv')

  source venv/bin/activeate (to activate the virtual environment)

  pip3 install -r requirements.txt (to install the python requirements for opennetem)

