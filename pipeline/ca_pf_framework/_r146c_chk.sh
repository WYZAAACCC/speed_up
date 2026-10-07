#!/bin/bash
# _r146c_chk.sh —— 自检在**合法几何**上跑一次（N=48 单块，最省）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1 MALLOC_MMAP_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
rm -rf _exp/_bk_cvchk
$PY -u _bk_exp.py --arm dry --N 48 --dx-nm 62.5 --steps 20 --every 20 \
  --plate-L 1200 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
  --laths 1,1,1 --facet-proj 5 \
  --tag cvchk --out _exp/_bk_cvchk > _w2_r146c.log 2>&1
echo "rc=$?"
echo "--- 自检输出 ---"
grep -n '块内界面自检\|cov_norm\|β 占比\|块内.*没过\|播种 ' _w2_r146c.log
echo
echo "--- 上下文（播种行起 12 行）---"
awk '/^播种 /{f=1} f{print; n++} n>=12{exit}' _w2_r146c.log
