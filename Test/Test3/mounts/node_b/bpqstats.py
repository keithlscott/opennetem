#!/usr/bin/env python3

#Reporting detail of all bundles.
#Current ctime sec 1707225774
#Event ctime sec   1707229364
#
#**** Bundle
#Source EID      'ipn:1.3'
#Destination EID 'ipn:3.1'
#Report-to EID   'ipn:1.3'
#Creation msec   331752911   count         55   frag offset          0
#- is a fragment:        0

class bpqstats_processor(object):
    def __init__(self):
        self.data = None
        self.records = []
        self.cur_record = {}
        return

    def get_data(self):
        if True:
            print("Reading from foo.txt")
            with open("foo.txt", "r") as fp:
                data = fp.read()
        else:
            pass
            # run bplist and capture output

        return(data)

    def process_data(self):
        if self.data==None:
            self.data = self.get_data()

        lines = self.data.split("\n")
        for l in lines:
            if l.find("**** Bundle")>=0:
                if len(self.cur_record)>0:
                    self.records += [self.cur_record]
                self.cur_record = {}
            if l.find("Source EID")>=0:
                toks = l.split()
                self.cur_record["source_eid"] = toks[2].replace("'", "")
            if l.find("Destination EID")>=0:
                toks = l.split()
                self.cur_record["dest_eid"] = toks[2].replace("'", "")
            if l.find("Payload len")>=0:
                toks = l.split()
                self.cur_record["payload_len"] = int(toks[2])
        if len(self.cur_record)>0:
            self.records += [self.cur_record]
        
        return(self.records)

    # For each unique (src, dst) pair, report the number of bundles and
    # bytes we're holding that match.
    def histogram(self):
        pairs = {}
        for r in self.records:
            print(r)
            key = (r["source_eid"], r["dest_eid"])
            if (key) not in pairs:
                pairs[key] = {}
                pairs[key]["num_bundles"] = 0
                pairs[key]["total_bytes"] = 0
            pairs[key]["num_bundles"] += 1
            pairs[key]["total_bytes"] += r["payload_len"]
        return(pairs)

    def records(self):
        return(self.records)

def main():
    proc = bpqstats_processor()
    records = proc.process_data()
    print(len(records))
    print(records)
    hist = proc.histogram()
    print(hist)


if __name__=="__main__":
    main()

