#!/usr/bin/env python3

import statsd
import socket
import random

c = statsd.StatsClient('localhost', 9125, prefix='netemcontroller')
#c.incr('bar')  # Will be 'foo.bar' in statsd/graphite.
#c.decr('bar')  # Will be 'foo.bar' in statsd/graphite.
c.set('bar', 1)  # Will be 'foo.bar' in statsd/graphite.
c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName1", "label2": "if1"})
c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName1", "label2": "if2"})
c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName2", "label2": "if1"})
c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName2", "label2": "if2"})
c.gauge(f"guageName", random.randint(0,10), tags={"label1":"hostName3", "label2": "if1"})


