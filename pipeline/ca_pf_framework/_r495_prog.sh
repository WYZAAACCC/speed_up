#!/usr/bin/env bash
# R495 —— R492 集成冒烟的进度查看（避免 PowerShell 引号问题）
set -u
cd "$(dirname "$0")"
for T in r492on r492off; do
  echo "--- $T ---"
  F="_w2_r492_${T}.log"
  C="_exp/_bk_mb/dry_${T}/series.csv"
  if [ -f "$C" ]; then printf '  CSV 行数: %s\n' "$(wc -l < "$C")"; else echo "  （无 CSV）"; fi
  if [ -f "$F" ]; then
    printf '  Traceback: %s\n' "$(grep -c 'Traceback' "$F" || true)"
    printf '  qs 档行:   %s\n' "$(grep -c 'qs] 档' "$F" || true)"
    printf '  athermal 形核行: %s\n' "$(grep -c 'athermal 形核' "$F" || true)"
    printf '  最后一行: %s\n' "$(tail -1 "$F" | cut -c1-90)"
  fi
done
echo "--- 进程 ---"
ps -eo pid,etimes,pcpu,args --sort=-pcpu | grep '[_]bk_exp' | cut -c1-64
echo "--- 资源 ---"
uptime
