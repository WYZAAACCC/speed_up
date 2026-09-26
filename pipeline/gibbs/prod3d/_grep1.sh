#!/bin/bash
set +u
H=/root/miniconda3/envs/moose/include/libmesh/fparser_ad.hh
echo "=== grep max/min/if ==="
grep -n "max\|min\|Abs\|floor\|ceil" $H | head -40
echo "=== ????? .cc ==="
find /root/miniconda3/envs/moose -name "fparser_ad*" 2>/dev/null
find /root/moose -name "fparser_ad*" 2>/dev/null | head
