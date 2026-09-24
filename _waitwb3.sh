#!/bin/bash
for i in $(seq 1 100); do
  if ! pgrep -f 'windowB_bench' > /dev/null; then break; fi
  sleep 15
done
cat /tmp/wb3.log