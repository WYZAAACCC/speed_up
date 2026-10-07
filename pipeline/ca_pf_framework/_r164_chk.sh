#!/bin/bash
# _r164_chk.sh —— `--f2-pair-gamma` 的接线核对（语法 + λ=0 惰性 + λ>0 生效）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1 MALLOC_MMAP_THRESHOLD_=65536 MALLOC_ARENA_MAX=2
echo "=== 语法 ==="
$PY -c "import ast; ast.parse(open('_bk_exp.py').read()); ast.parse(open('windowB_lath.py').read()); print('OK')"
echo
echo "=== 板条表自检（确认没改坏 `windowB_lath`）==="
$PY windowB_lath.py --selftest 2>&1 | tail -3
echo
echo "=== λ=0（默认）：F2 应仍写 '退回标量'，且不填 gtab ==="
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 0 --every 20 \
  --plate-L 1000 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
  --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 700 \
  --tag f2lam0 --out _exp/_bk_f2 2>&1 | grep -E 'F2\(γ|F3 γ_RS|F2 的配对依赖' | head -6
echo
echo "=== λ=1：应打印 λ/Δε_ref/F2 对数，并把 F2 面能填成配对值 ==="
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 0 --every 20 \
  --plate-L 1000 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
  --laths 1,1,3,3,5,5 --multi-block --block-gap-nm 700 \
  --f2-pair-gamma 1.0 \
  --tag f2lam1 --out _exp/_bk_f2 2>&1 | grep -E 'F2\(γ|F3 γ_RS|F2 的配对依赖|公式|目标不同' | head -10
