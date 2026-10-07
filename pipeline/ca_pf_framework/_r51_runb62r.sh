#!/bin/bash
# R51: 按 **PID** 杀 b62q（不用 pgrep -f —— 上一次它匹配到自己的 shell 并自杀，见 AGENTS.md §3.10），
#       然后启动 b62r。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

for P in 32181; do
  if [ -d /proc/$P ]; then
    CMD=$(tr '\0' ' ' < /proc/$P/cmdline 2>/dev/null | grep -oE '\-\-tag [A-Za-z0-9_]+')
    echo "kill $P  ($CMD)"
    kill -9 "$P"
  else
    echo "$P 已不在"
  fi
done
sleep 2

echo "=== 启动 b62r（B‴：--block-gap-nm 3000 > plate-L 2000）"
"$PY" -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,2,2,2 --multi-block --block-gap-nm 3000 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 60 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62r --out _exp/_bk_mb > _w2_r51_b62r_smoke.log 2>&1
rc=$?
echo "=== b62r rc=$rc $(date '+%F %T')"
echo "--- J-0"
"$PY" _r51_b62chk.py _exp/_bk_mb/dry_b62r/series.csv 2>&1 | tail -3
