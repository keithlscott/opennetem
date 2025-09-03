#!/usr/bin/env python3

# Tue Feb  6 08:48:03 UTC 2024 ==== 483: 64 bytes from ipn:3.1  seq=409 time=68.098794 s
def bping_stats(filename):
    with open(filename) as fp:
        data = fp.read()
        lines = data.split("\n")

    seqnos = []
    rtts = []
    for l in lines:
        if l.find("seq=")<0:
            continue
        toks = l.split("seq=")
        toks2 = toks[1].split()
        seqno = int(toks2[0])
        seqnos += [seqno]
        toks3 = l.split("time=")
        toks4 = toks3[1].split()
        rtt = float(toks4[0])
        rtts += [rtt]

    print(f"Min seqno:               {min(seqnos)}")
    print(f"Max seqno:               {max(seqnos)}")
    print(f"Total number of replies: {len(seqnos)}")
    print(f"Seqno delta:             {max(seqnos)+1-min(seqnos)}")
    seqno_set = set(seqnos)
    print(f"Num unique seqnos seen:  {len(seqno_set)}")

    print(f"Min RTT: {min(rtts):.2f}")
    print(f"Max RTT: {max(rtts):.2f}")
    print(f"Ave RTT: {sum(rtts)/len(rtts):.2f}")


bping_stats("bping_3.1.out")

