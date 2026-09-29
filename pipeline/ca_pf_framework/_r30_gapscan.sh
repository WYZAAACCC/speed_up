#!/bin/bash
# _r30_gapscan.sh —— 扫多块播种的块心间距，找出"t=0 真正分离"的那一档。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
for G in 4000 5000 6000 7000; do
  "$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 125 \
    --laths 1,1,1,3,3,3 --multi-block --block-gap-nm "$G" \
    --plate-L 4590 --plate-W 1224.153 --plate-T 635 --plate-t-physical 510 \
    --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 \
    --steps 1 --every 1 --snap-every 1 --pair-every 1 --nthreads 2 \
    --tag "g$G" --out _exp/_r30mfix > "_w2_r31g$G.log" 2>&1
  echo "=== gap = $G nm ==="
  grep -aE '质心距|精确判据' "_w2_r31g$G.log" | head -3
done
