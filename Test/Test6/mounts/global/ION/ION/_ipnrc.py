# ipnrc file of the form:
# a plan 1 ltp/1
# a plan 2 udp/127.0.0.1:4556
# a plan 3 tcp/10.45.7.2:4556
import logging
import os

logger = logging.getLogger("ion_config_tool").getChild("ipnrc")

def write_ipnrc(self):
    logger.info(f"writing ipnrc for {self.node_name}; outducts are: {self.outducts}")

    the_filename = f"{self.output_directory}/{self.node_name}.ipnrc"
    if os.path.exists(the_filename):
        os.remove(the_filename)

    if len(self.outducts)==0:
        logger.warning(f"NO OUTDUCTS for {self.node_name}")
        with open(the_filename, "w") as fp:
            fp.write("# NO OUTDUCTS\n")
        return
    
    with open(the_filename, "w") as fp:
        for outduct in self.outducts:
            if outduct.protocol in ["tcp", "udp"]:
                fp.write(f"a plan {outduct.dest_node_number} {outduct.protocol}/{outduct.dest_identifier}:4556\n")
            if outduct.protocol in ["ltp"]:
                fp.write(f"a plan {outduct.dest_node_number} {outduct.protocol}/{outduct.dest_node_number}\n")

