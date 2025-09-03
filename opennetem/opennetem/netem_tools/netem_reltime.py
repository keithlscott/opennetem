#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import json
import os
import time

class Reltime(object):
    def __init__(self):
        self.info_file = "/netem/globals/instance_info.json"
        self.reset()

    def reset(self, start_time=None):
        if start_time != None:
            self.start_time = start_time
        elif os.path.isfile(self.info_file):
            with open(self.info_file) as fp:
                data = fp.read()
                info = json.loads(data)
            self.start_time = info["start_time"]
        else:
            self.start_time = time.time()

    def get_reltime(self):
        return(time.time()-self.start_time)


if __name__=="__main__":
    foo = Reltime()
    time.sleep(4)
    print(foo.get_reltime())
