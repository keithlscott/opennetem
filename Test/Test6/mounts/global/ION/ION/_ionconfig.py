#!/usr/bin/env python
import os

def write_ionconfig(self):
    the_filename = f"{self.output_directory}/{self.node_name}.ionconfig"
    if os.path.exists(the_filename):
        os.remove(the_filename)

    with open(the_filename, "w") as fp:
        fp.write(f"""\
# CONFIGFLAGS\n\
# [1] ion configuration flags : 13 [SDR_IN_DRAM + SDR_REVERSIBLE + SDR_BOUNDED]\n\
configFlags 13\n""")

