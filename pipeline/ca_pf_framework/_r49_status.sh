#!/bin/bash
# R49: 统一查看所有正在跑的臂的进度（不依赖 Windows 侧引号）
cd /mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb || exit 1
echo "=== _bk_mb ==="
for d in dry_mb1L dry_mb1Ls dry_mb1s62 dry_mb1 dry_mb1s eng_mb2 eng_mb3 eng_mb2b eng_mb3b eng_mb2c eng_mb3c; do
  [ -d "$d" ] || continue
  if [ -f "$d/run.log" ]; then
    last=$(grep -oE 'step +[0-9]+' "$d/run.log" | tail -1)
    ns=$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)
    nphi=$(ls "$d"/phi_*.npz 2>/dev/null | wc -l)
    printf '%-12s %-14s snap=%-4s phi=%-4s size=%s\n' "$d" "${last:-?}" "$ns" "$nphi" "$(du -sh "$d" 2>/dev/null | cut -f1)"
  else
    printf '%-12s (no run.log)\n' "$d"
  fi
done
echo "=== _bk_closed ==="
cd ../_bk_closed 2>/dev/null && for d in dry_cln11 dry_cln2 dry_cln2b; do
  [ -f "$d/run.log" ] || continue
  last=$(grep -oE 'step +[0-9]+' "$d/run.log" | tail -1)
  printf '%-12s %-14s snap=%s\n' "$d" "${last:-?}" "$(ls "$d"/snap_*.npz 2>/dev/null | wc -l)"
done
echo "=== python procs (pid pcpu rssMB etimes cmd) ==="
ps -eo pid,pcpu,rss,etimes,args --no-headers | grep -E '_bk_exp|ca_pf' | grep -v grep | while read -r pid pcpu rss et args; do
  printf '%s %5s%% %6dMB %6ss %s\n' "$pid" "$pcpu" "$((rss/1024))" "$et" "$(echo "$args" | cut -c1-110)"
done
echo "=== mem ==="; free -g | head -2
echo "=== load ==="; uptime
