#!/usr/bin/env bash
# _kick_when.sh --- 杀掉 dte 作业（按 PID，排除自己），再启动 when 作业
set -u
SELF=$$
for P in $(ps -eo pid,args | grep -e "_r1_reinit_dte.py" | grep -v grep | awk '{print $1}'); do
  [ "$P" = "$SELF" ] && continue
  echo "kill -9 $P"
  kill -9 "$P" 2>/dev/null
done
sleep 2
echo "--- 残留 ---"
ps -eo pid,args | grep -e '_r1_reinit' | grep -v grep || echo "(无)"
cd /mnt/f/speed_up/pipeline/ca_pf_framework
exec bash _run_r1.sh _r1_reinit_when.py _w2_r1reinit_when.log 1700
