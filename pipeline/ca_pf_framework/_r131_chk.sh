#!/bin/bash
# _r131_chk.sh —— 语法检查 + 新开关自检 + 正对照打印
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export PYTHONDONTWRITEBYTECODE=1
echo "=== 语法 ==="
$PY -c "import ast; ast.parse(open('_bk_exp.py').read()); print('OK')"
echo
echo "=== 新开关在不在 ==="
$PY -u _bk_exp.py --help 2>&1 | grep -A3 'rank1-swap' | head -6
echo
echo "=== `--rank1-swap invariant` 的**正对照 + 受影响集合**（只构造、跑 0 步）==="
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 0 --every 20 \
  --laths 1,1,1,3,3,3 --rank1-swap invariant --tag swaptest \
  --out _exp/_bk_swap 2>&1 | grep -E '选支|受影响|V[0-9]+ +rB|PASS|✗' | head -14
echo
echo "=== 对照：默认 `none` 不打印那些行（且应逐位不变）==="
$PY -u _bk_exp.py --arm dry --N 32 --dx-nm 62.5 --steps 0 --every 20 \
  --laths 1,1,1,3,3,3 --tag swaptest0 \
  --out _exp/_bk_swap 2>&1 | grep -cE '选支受控对照' || true
