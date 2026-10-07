#!/bin/bash
# _r1_v6dbg.sh --- 队列 v6 为何仍未启动 a3_facet00
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
P=$(pgrep -f 'bash _r1_drive6.sh' | head -1)
echo "v6 pid = ${P:-（不在）}"
if [ -n "$P" ]; then
  echo "state  = $(ps -o stat= -p "$P" | tr -d ' ')"
  echo "etimes = $(ps -o etimes= -p "$P" | tr -d ' ') s"
  echo "wchan  = $(cat /proc/$P/wchan 2>/dev/null)"
  echo "子进程："
  ps --ppid "$P" -o pid,stat,args --no-headers 2>/dev/null | head -5
  echo "栈（bash 正在跑什么）："
  cat /proc/$P/cmdline | tr '\0' ' '; echo
fi
echo
echo "=== 它写的日志 ==="
wc -l < _w2_r1drive6.log
tail -5 _w2_r1drive6.log
echo
echo "=== 现在真正活跃的算例（锚定口径）==="
pgrep -c -f '^/root/miniconda3/envs/ml/bin/python -u _r1_exp\.py'
echo "=== a3_facet00 目录 ==="
ls -la _exp/a3_facet00 2>/dev/null || echo "（不存在）"
