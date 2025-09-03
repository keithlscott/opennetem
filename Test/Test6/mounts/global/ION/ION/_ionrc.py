import os

def write_ionrc(self):
    the_filename = f"{self.output_directory}/{self.node_name}.ionrc"
    if os.path.exists(the_filename):
        os.remove(the_filename)

    with open(the_filename, "w") as fp:
        fp.write(f"""
#####
# 1 <NODE_NUMBER>
1 {self.node_number}
#
# START
s
""")
