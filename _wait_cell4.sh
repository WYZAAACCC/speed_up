#!/bin/bash
for i in $(seq 1 120); do
  if ! pgrep -f '[_]ti64_cell' > /dev/null; then break; fi
  sleep 15
done
cat /mnt/f/speed_up/_ti64_cell4.log