#!/usr/bin/env bash
# _r330_prog.sh -- 进度/负载检查（避免 PowerShell 内联引号被吞）
R=/mnt/f/speed_up/pipeline/ca_pf_framework
D=$R/_exp/_bk_mb
cd "$D" || exit 1
echo "=== arms ==="
for n in saSet2P0 saSet2F2P0 near200 mid200 far200 saSet2EDV; do
  if [ -f "$n/snapshots.csv" ]; then
    nline=$(wc -l < "$n/snapshots.csv")
    last=$(tail -1 "$n/snapshots.csv" | cut -d, -f1-2)
    printf "%-12s lines=%-6s last=%s\n" "$n" "$nline" "$last"
  else
    printf "%-12s (no csv)\n" "$n"
  fi
done
echo "=== procs ==="
ps -eo pid,etime,pcpu,rss,args --sort=-pcpu | grep -E '_bk_exp[.]py' | head -12
echo "=== mem/load ==="
free -g | head -2
uptime
echo "=== threads ==="
mpstat 1 1 2>/dev/null | tail -3
