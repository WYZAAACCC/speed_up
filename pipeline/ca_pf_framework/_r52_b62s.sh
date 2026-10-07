#!/bin/bash
# R52: 验证 P1-30 的修复 —— 只跑 20 步的冒烟，看**块心间距是否精确兑现**。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

$PY -c "import ast;ast.parse(open('_bk_exp.py').read())" || { echo SYNTAX-FAIL; exit 1; }
echo "SYNTAX-OK"

rm -rf _exp/_bk_mb/dry_b62s
$PY -u _bk_exp.py --arm dry --N 144 --dx-nm 62.5 \
  --laths 1,1,1,2,2,2 --multi-block --block-gap-nm 3000 \
  --plate-L 2000 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 20 --every 20 --snap-every 20 --pair-every 20 --nthreads 3 \
  --tag b62s --out _exp/_bk_mb > _w2_r52_b62s.log 2>&1
echo "rc=$?  $(date '+%F %T')"
echo "--- 构型日志"
grep -E '块心|布局轴|精确判据|质心距|块[0-9]：' _w2_r52_b62s.log | head -8
echo "--- J-0 正对照"
$PY _r52_gapctrl.py b62s 3000 2>&1 | tail -5
