#!/bin/bash
# _r146b_chk.sh —— 自检在真算例上到底有没有打出来
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1 MALLOC_MMAP_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
rm -rf _exp/_bk_cvchk
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 20 --every 20 \
  --plate-L 1000 --plate-W 500 --plate-T 510 --plate-t-physical 400 \
  --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 900 \
  --tag cvchk --out _exp/_bk_cvchk > _w2_r146b.log 2>&1
echo "rc=$?"
echo "--- 含'自检'的行 ---"
grep -n '自检' _w2_r146b.log || echo "（没有）"
echo "--- 含 'cov' 的行 ---"
grep -n 'cov' _w2_r146b.log || echo "（没有）"
echo "--- 播种后的 30 行 ---"
grep -n '播种 ' _w2_r146b.log | head -2
sed -n "$(grep -n '播种 ' _w2_r146b.log | head -1 | cut -d: -f1),+14p" _w2_r146b.log
