#!/usr/bin/env bash
# _r735_diag.sh —— 诊断长 A/B：进程是否存活 / 卡在哪个 syscall / WSL 内存与 swap。
set -uo pipefail
echo "=== 1) 进程 ==="
PIDS=$(pgrep -f '[_]bk_exp.py' || true)
if [ -z "$PIDS" ]; then echo "  ⛔ **无 _bk_exp.py 进程**（已死或被 OOM 杀）"; else
  for P in $PIDS; do
    echo "  pid=$P etime=$(ps -o etime= -p $P|tr -d ' ') %cpu=$(ps -o pcpu= -p $P|tr -d ' ') rss=$(ps -o rss= -p $P|tr -d ' ')KB state=$(ps -o stat= -p $P|tr -d ' ')"
    echo "    wchan=$(cat /proc/$P/wchan 2>/dev/null)"
    echo "    last-syscall: $(cat /proc/$P/syscall 2>/dev/null | cut -d' ' -f1)"
  done
fi
echo
echo "=== 2) 内存与 swap ==="
free -m | sed 's/^/  /'
echo
echo "=== 3) OOM 痕迹（dmesg 里最近的内存杀）==="
dmesg 2>/dev/null | grep -i -E 'killed process|out of memory|oom' | tail -5 | sed 's/^/  /' || echo "  （dmesg 不可读或无记录）"
echo
echo "=== 4) 日志最后 3 行（有无 traceback）==="
tail -3 /mnt/f/speed_up/_w2_longab.log 2>/dev/null | cut -c1-120 | sed 's/^/  /'
echo
echo "=== 5) series.csv 与快照时间 ==="
D=/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_ndirlsq_long/dry_L_off
ls -la --time-style='+%H:%M:%S' "$D" 2>/dev/null | tail -6 | sed 's/^/  /'
