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
logger = logging.getLogger("netem")

def get_sublogger(name):
    return logging.getLogger("netem").getChild(name)

#
# the_dir should be the scenario dir if known.
#
def do_logging_config(the_dir):
    if the_dir==None:
        the_dir = os.getcwd()

    if os.path.exists(f"{the_dir}/logging.conf"):
        logging.config.fileConfig(f'{the_dir}/logging.conf')
        logging.info(f"Using logging.conf from {the_dir}")
    else:
        logging.config.fileConfig(f'{SOURCE_DIR}/logging.conf')
        logging.info(f"Using logging.conf from {SOURCE_DIR}")

