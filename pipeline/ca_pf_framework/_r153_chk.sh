#!/bin/bash
# _r153_chk.sh —— 语法 + 新断言自检（回归 + 单场算例）
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "=== 语法 ==="
$PY -c "import ast; ast.parse(open('_bk_exp.py').read()); print('OK')"
echo
echo "=== 判据适用域：单场（--laths 1，t=0 只有 1 根）应说'不适用'而不是 ❌ ==="
$PY -u _bk_exp.py --arm dry --N 48 --dx-nm 62.5 --steps 0 --every 20 \
  --plate-L 1200 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
  --laths 1 --tag na1 --out _exp/_bk_na 2>&1 | grep -A2 '块内界面自检' | head -4
echo
echo "=== 对照：多根时应给出真判据（不应说不适用）==="
$PY -u _bk_exp.py --arm dry --N 48 --dx-nm 62.5 --steps 0 --every 20 \
  --plate-L 1200 --plate-W 500 --plate-T 400 --plate-t-physical 300 \
  --laths 1,1,1 --tag na3 --out _exp/_bk_na 2>&1 | grep -A3 '块内界面自检' | head -5
