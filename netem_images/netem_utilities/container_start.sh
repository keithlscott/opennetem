#!/bin/bash
# /usr/sbin/collectd

/usr/local/bin/reltime_server.py >& /dev/null &

tail -f /dev/null
