#!/bin/bash
# _audit_kill.sh --- 只杀 cwd 在 ca_pf_framework 下的遗留 python（不用 pkill -f，见 AGENTS §3.10/3.11）
for P in $(pgrep -x python); do
  CWD=$(readlink /proc/$P/cwd 2>/dev/null)
  case "$CWD" in
    *ca_pf_framework*) echo "kill $P -> $CWD"; kill -9 "$P";;
  esac
done
sleep 2
echo "--- remaining python ---"
pgrep -a python || echo "(none)"
