# INITIALIZE
# [1] est max export sessions : 10
# 1 10
#
# SPAN_UDP
# [1] peer engine number : 1
# [2] max export sessions : 10
# [3] max import sessions : 10
# [4] max segment size : 64000 (bytes)
# [5] aggregation size limit : 100000 (bytes)
# [6] aggregation time limit : 1 (secs)
# [7] udp link service name : 10.0.1.1:1113
# [8] transmission rate : 1000000 (bits per sec)
# [9] queueing latency : (secs)
# a span 1 10 10 64000 100000 1 'udplso 10.44.3.1:1113 1000000'
#
# START_UDP
# [1] ip address (or name) : 10.0.1.2
# [2] local port number : 1113
# s 'udplsi 10.44.3.2:1113'

import os
import logging

logger = logging.getLogger("ion_config_tool").getChild("bprc")

def write_ltprc(self):
    logger.info(f"Starting write_ltprc for {self.node_name}")

    the_filename = f"{self.output_directory}/{self.node_name}.ltprc"
    if os.path.exists(the_filename):
        os.remove(the_filename)

    protos = [x for x in self.protocols]
    if "ltp" not in protos:
        logger.info(f"No ltp for node {self.node_name}")
        return
    
    logger.info(f"writing ltprc file for {self.node_name}")
    with open(the_filename, "w") as fp:
        fp.write("1 10\n\n")
        ltp_outducts = [outduct for outduct in self.outducts if outduct.protocol=="ltp"]
        for outduct in ltp_outducts:
            fp.write(f"a span {outduct.dest_node_number} 10 10 64000 100000 1 'udplso {outduct.dest_identifier}:1113 1000000'\n")
        ltp_inducts = [induct for induct in self.inducts if induct.protocol=="ltp"]
        if len(ltp_inducts)>0:
            fp.write("s 'udplsi 0.0.0.0:1113'\n")
