#!/usr/bin/env python3

#
# Copyright (C) 2024 Keith Scott <keithlscott@gmail.com>
# GNU Public License Version 3, 29 June 2007
#

import os
import logging
import logging.config
import time
import os

logging_start_time = None

SOURCE_DIR = os.path.dirname(os.path.realpath(__file__))

# logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')
# logger = logging.getLogger("opennetem")

def get_sublogger(name, parent=None):
    if ( parent==None):
        return(logging.getLogger("opennetem").getChild(name))
    if type(parent)==type(""):
        return logging.getLogger(parent).getChild(name)
    
    return logging.getLogger(parent.name).getChild(name)

#
# the_dir should be the scenario dir if known.
#
def do_logging_config(the_dir):
    print(f"do_logging_config called with dir: {the_dir}")

    for test_dir in [f"{the_dir}",
                     f"{os.getcwd()}",
                     f"{os.path.expandvars('$HOME')}",
                     f"/etc/opennetem",
                     f"{SOURCE_DIR}"]:
        print(f"do_logging_config looking for log file at {test_dir}")
        if os.path.exists(f"{test_dir}/logging.conf"):
            logging.info(f"Using logging.conf: {test_dir}/logging.conf")
            logging.config.fileConfig(f"{test_dir}/logging.conf")
            break

    logger = logging.getLogger("opennetem")
    logger.info("Done configuring logging.")

