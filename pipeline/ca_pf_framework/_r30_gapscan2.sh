#!/bin/bash
# _r30_gapscan2.sh —— 在**更短的种子**下扫多块几何，找出 t=0 **真正分离**（F2=0）的配置。
#   物理动机：真实板条是**从小核长大**的；把种子播短、让它在跑的过程中长到相遇，
#   才是"两块相遇"的正确装置（且 12 µm 盒装得下两块各 ~4 µm 的板条）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
for PL in 1600 2400; do
  for G in 5000 7000; do
    T="pl${PL}_g${G}"
    "$PY" -u _bk_exp.py --arm dry --N 96 --dx-nm 125 \
      --laths 1,1,1,3,3,3 --multi-block --block-gap-nm "$G" \
      --plate-L "$PL" --plate-W 700 --plate-T 635 --plate-t-physical 510 \
      --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 \
      --steps 1 --every 1 --snap-every 1 --pair-every 1 --nthreads 2 \
      --tag "$T" --out _exp/_r30mfix > "_w2_r31$T.log" 2>&1
    echo "=== plate-L=$PL  gap=$G ==="
    grep -aE '质心距|精确判据|余量' "_w2_r31$T.log" | head -3
  done
done
