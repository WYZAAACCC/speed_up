#!/bin/bash
cd /mnt/f/speed_up/pipeline/ca_pf_framework/pf1d_moose || exit 1
# 1) stop every running instance of the instrument (find PIDs first, never pkill blindly)
for p in $(ps -eo pid,args | grep 'p1c_prod1d.py' | grep -v grep | awk '{print $1}'); do kill -9 $p; done
sleep 2
echo "remaining: $(ps -eo args | grep -c 'p1c_prod1d.py')"
# 2) show the mixed dirs
for d in prod1d_A0_W2_kc1e-14 prod1d_A2_W2_kc1e-14; do
  echo "== $d"; ls $d | grep -c 'profile_line'; ls -la $d/profile_line_*.csv 2>/dev/null | tail -2
done