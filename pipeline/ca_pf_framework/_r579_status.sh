#!/bin/bash
# _r579_status.sh --- 并行批次状态一览
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
echo "=== orchestrator ==="
tail -16 _w2_r579_par_orchestrator.log
echo
echo "=== 各道最后一行 ==="
for f in T MA1 MA2 MB1 MB2 G P R; do
  L="_w2_r579_par_$f.log"
  if [ -f "$L" ]; then
    printf '%-5s %s\n' "$f" "$(tail -1 "$L" | cut -c1-130)"
  else
    printf '%-5s (无日志)\n' "$f"
  fi
done
echo
echo "=== 进程 ==="
ps -eo pid,pcpu,etimes,args --sort=-pcpu | grep -E 'python|taskset' | grep -v grep | head -10
echo
echo "=== 资源 ==="
uptime; free -m | head -2
