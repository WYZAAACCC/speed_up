#!/bin/bash
# kill only our probe python processes, by exact pid, never pkill -f
for P in $(pgrep -f "_probe_cost.py" 2>/dev/null); do
  echo "kill $P : $(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)"
  kill -9 "$P" 2>/dev/null
done
for P in $(pgrep -f "_probe_" 2>/dev/null); do
  echo "kill $P : $(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null)"
  kill -9 "$P" 2>/dev/null
done
sleep 3
echo "=== remaining ==="
ps -eo pid,etimes,args | grep -E "_probe|_sim|windowB" | grep -v grep
echo "=== mem ==="
free -g
