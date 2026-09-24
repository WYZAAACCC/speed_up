#!/bin/bash
for i in $(seq 1 40); do
  if ! ps -eo args | grep -q '[_]exaca_mirror'; then break; fi
  sleep 20
done
cat /mnt/f/speed_up/_exaca_mirror.log
echo "--- 是否还在跑:"; ps -eo etime,args | grep '[_]exaca_mirror' | head -1