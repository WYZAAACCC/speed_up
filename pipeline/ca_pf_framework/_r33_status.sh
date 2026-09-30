#!/bin/bash
# _r33_status.sh —— 一行看全部在跑的算例（避免 PowerShell 把 $f 吃掉）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
date
for T in mb1 mb1s mb2 mb3 mb2b mb3b mb2c mb3c mb1L mb1Ls; do
  for P in _w2_r31_ _w2_r37_ _w2_r40_; do
    L="${P}${T}.log"
    if [ -f "$L" ]; then
      printf '%-7s ' "$T"
      tail -1 "$L" | cut -c1-58
      break
    fi
  done
done
printf '%-6s ' cln11
tail -1 _w2_bk_cln11.log | cut -c1-64
echo "--- 进程（python -u）---"
ps -eo pid,etimes,pcpu,rss,args --sort=-pcpu | grep '[p]ython -u' | cut -c1-70
echo "--- 负载/内存 ---"
uptime
free -g | sed -n 2p
