#!/bin/bash
for i in $(seq 1 60); do
  if ! pgrep -f '[_]ti64_compare' > /dev/null; then break; fi
  sleep 15
done
cat /mnt/f/speed_up/_ti64_cmp.log