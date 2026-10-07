#!/usr/bin/env bash
# _r546_verdict_and_regress.sh —— ① ps_b3 的预登记判据 ② 默认路径回归
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "##################### ① ps_b3（B=3 + 周期播种）判据 #####################"
$PY -u _r540_b5verdict.py ps_b3 _exp/_bk_par 2>&1 | tail -14

echo
echo "##################### ② ps_b8（B=8 + 周期播种）读数 #####################"
$PY -u _r540_b5verdict.py ps_b8 _exp/_bk_par 2>&1 | tail -14

echo
echo "##################### ③ 默认路径回归（用户硬要求：逐位不变） #####################"
echo "  说明：三处改动全部挂在 `periodic_seed`（默认 False）后面；"
echo "        `_r543` 的 T3 已证 `seed_plate` 在盒内种子上 \`max|Δphi| = 0.000e+00\`。"
echo "  这里再跑仓库现成的回归脚本："
if [ -f _r30_regress.sh ]; then
  bash _r30_regress.sh 2>&1 | tail -30
else
  echo "  ⚠ 找不到 _r30_regress.sh"
fi
