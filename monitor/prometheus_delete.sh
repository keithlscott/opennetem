#!/bin/bash

#
# Delete data from prometheus.
# Useful when building 'blank' container volumes for distribution.
#

curl -X POST -g 'localhost:9090/api/v1/admin/tsdb/delete_series?match[]={__name__="latency_monitor_latency"}'
curl -X POST -g 'localhost:9090/api/v1/admin/tsdb/delete_series?match[]={__name__="netem_scenario_netem_event"}'

