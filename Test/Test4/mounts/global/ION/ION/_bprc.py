import logging
import os

logger = logging.getLogger("ion_config_tool").getChild("bprc")


def write_bprc(self):
    the_filename = f"{self.output_directory}/{self.node_name}.bprc"
    if os.path.exists(the_filename):
        os.remove(the_filename)

    logger.info(f"in write_bprc protocols is: {self.protocols}")
    logger.info(f"in write_bprc inducts is:   {self.inducts}")
    logger.info(f"in write_bprc outducts is:  {self.outducts}")

    with open(the_filename, "w") as fp:
        fp.write("""\
# INITIALIZE
1

#
# SCHEME
# [1] scheme name : ipn [Interplanetary Overlay Network Scheme]
# [2] forwarder command : ipnfw [ION Forwarder]
# [3] admin app command : ipnadminep [ION Admin Endpoints]
a scheme ipn 'ipnfw' 'ipnadminep'

#
# ENDPOINT
# [1] node num : {self.node_number}
# [2] service num : 1 [BP Echo]
# [3] bundle disposition : x [discard undeliverable bundles]
# [4] queue receiver task :
# a endpoint ipn:{self.node_number}.1 x

""")
        #
        # Endpoints
        #
        for i in range(1, self.num_services+1):
            fp.write(f"a endpoint ipn:{self.node_number}.{i} x\n")

        #
        # LTP protocol
        #
        if "ltp" in self.protocols:
            fp.write(f"""\

###################################
#
# LTP
#
# PROTOCOL
# [1] protocol name : ltp [Licklider Transmission Protocol]
# [2] payload bytes per frame : 1400 (bytes)
# [3] overhead bytes per frame : 100 (bytes)
# [4] nominal data rate : 1000000 (bytes per sec)
a protocol ltp 1400 100 1000000

""")
        else:
            fp.write("""
###################################
# NO LTP
""")
        #
        # LTP inducts
        #
        ltp_inducts = [d for d in self.inducts if d.protocol=="ltp"]
        for induct in ltp_inducts:
            fp.write(f"""\
#
# INDUCT_LTP
# [1] ltp duct name : {self.node_number}
# [2] ltp cli task name : ltpcli
a induct ltp {self.node_number} ltpcli

""")

        #
        # LTP outducts
        #
        ltp_outducts = [d for d in self.outducts if d.protocol=="ltp"]
        for outduct in ltp_outducts:
            fp.write(f"a outduct ltp {outduct.dest_node_number} ltpclo 1500\n")

        fp.write("###################################\n\n")

        #
        # UDP
        #
        if "udp" in self.protocols:
            fp.write(f"""\
###################################
#
# UDP
#
# PROTOCOL
# [1] protocol name : udp
# [2] dest
a protocol udp 1400 100 1000000

""")

        else:
            fp.write("""
###################################
# NO UDP
""")
        #
        # UDP indudcts
        #
        if "udp" in self.inducts:
            fp.write(f"""\
#
# INDUCT_UDP
a induct udp 0.0.0.0:4556 udpcli
                    
""")
        

        #
        # UDP outducts
        #
        udp_outducts = [d for d in self.outducts if d.protocol=="udp"]
        if len(udp_outducts)==0:
            logger.info(f"NO UDP outducts for {self.node_name}")
        for outduct in udp_outducts:
            fp.write(f"a outduct udp {outduct.dest_identifier} udpclo\n")
        
        fp.write("###################################\n\n")

        #
        # TCP Protocol
        #
        if "tcp" in self.protocols:
            fp.write(f"""\
###################################
#
# TCP
#
# PROTOCOL
# [1] protocol name : tcp
# [2] payload bytes per frame : 1400 (bytes)
# [3] overhead bytes per frame : 100 (bytes)
# [4] nominal data rate : 1000000 (bytes per sec)
a protocol tcp 1400 100 1000000

""")
        else:
            fp.write(f"""
###################################
# No TCP\n""")

        #
        # TCP inducts
        #
        if "tcp" in [x.protocol for x in self.inducts]:
            fp.write("""a induct tcp 0.0.0.0:4556 tcpcli

""")

        #
        # TCP outducts
        #
        tcp_outducts = [d for d in self.outducts if d.protocol=="tcp"]
        for od in tcp_outducts:
            fp.write(f"a outduct tcp {od.dest_identifier}\n\n")

        fp.write("###################################\n\n")

        fp.write(f"""r 'ipnadmin {self.node_name}.ipnrc\n\n""")

        fp.write(f"""w 1\n""")

        fp.write(f"""s\n""")
