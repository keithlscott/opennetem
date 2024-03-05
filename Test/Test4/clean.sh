#!/bin/bash

find . -name ion.env  | xargs rm -f
find . -name "*.bprc" | xargs rm -f
find . -name "start_ion.out" | xargs rm -f
find . -name "*.ionconfig" | xargs rm -f
find . -name "*.ionrc" | xargs rm -f
find . -name "*.ionsecrc" | xargs rm -f
find . -name "*.ipnrc" | xargs rm -f
find . -name "ion_config_tool.log" | xargs rm -f
find . -name "start_ion2.log" | xargs rm -f
find . -name "bpecho.out" | xargs rm -f
find . -name "ion.log" | xargs rm -f
find . -name "netem.log" | xargs rm -f
find . -name "__pycache__" | xargs rm -rf

