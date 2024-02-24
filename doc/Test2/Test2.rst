======
Test2
======

This test uses an frr router container and runs OSPF in the
nodes.  It also adds static arp entries to the nodes so
we don't have to deal with ARP

Caveat: to make this work, I have to add the static ARP entry
after quite a delay (on the order of 30--40 seconds).  I think
it's interacting with OSPF, so if OSPF downs the route through
that interface it might reset static arp; haven't checked that
yet.

The topology is a simple linear topology of three nodes (node_a,
node_b, and node_c) that are fully connected for five minutes.

This test uses a ``setup_ospf.py`` script that is invoked after
the node is set up and OSPF is running.  The script examines
the node's interfaces and executes ``vtysh`` commands to set
the ospf router-id and to enable all interfaces for ospf
except ``dock``, ``mon``, and ``lo``.