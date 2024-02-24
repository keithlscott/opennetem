==============
Monitoring
==============

netem provides a monitoring stack that can be started with ``docker compose up -d``
from the ``NETEM_INSTALL_DIR/monitor`` directory.

The monitoring stack consists of:

monitor-prometheus-1
====================

monitor-statsd_exporter-1
==========================
A statsd server to which clients in containers can send data that will be scraped
by the Prometheus server.  Note that the Prometheus server scraps statsd every
15s and pulls only the latest stats, so fine-grained behaviors may be missed.

monitor-collectd-1
==================

influxDB
========
influxDB provides a fine-grained time-series database useful for detailed inspection of behaviors.
For example, the ``ping_monitor.py`` script that mounts into ``/netem/netem_tools`` logs information
to influxDB for every ping response, allowing Grafana to graph the time-variant properties of the
network down to the order of seconds.

Grafana
=======
Grafana is the graphing front-end to the Prometheus and influxDB databases.
