#!/usr/bin/env python3

import datetime

with open("foo.out", "r") as fp:
    data = fp.read()
    lines = data.split("\n")

for l in lines:
    if len(l)<10:
        continue

    toks = l.split(",")

    # Given date string
    #date_string = "Thu Feb 15 18:01:40 UTC 2024"

    # Parse the date string into a datetime object
    try:
        date_object = datetime.datetime.strptime(toks[0], "%a %b %d %H:%M:%S UTC %Y")
    except Exception as e:
        print(f"Failed on line {l} with {e}.")

    # Convert datetime object to seconds since epoch
    seconds_since_epoch = date_object.timestamp()

    seqno = int(toks[1])

    print(f"{int(seconds_since_epoch)} {seqno}")

