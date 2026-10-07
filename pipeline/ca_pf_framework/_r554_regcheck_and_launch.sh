#!/usr/bin/env bash
# _r554_regcheck_and_launch.sh —— ① 明确核验回归的"共有列逐位一致" ② 启动 4 µm 的 C1–C6 算例组
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python

echo "##################### ① 回归判据核验（_w2_r30_regress.log）"
grep -n "共有列逐位一致\|差异\s*=\|FAIL" _w2_r30_regress.log | head -10

echo
echo "##################### ② 启动 4 µm 的 C1–C6 算例组（2 并发 × 各 4 线程，f32）"
echo "  依据：R550 §6 —— `--phi-prec f32` 已过 P1–P5，内存减半；"
echo "        4 µm 盒填 30% 要 75 根，f32 下每 nv 1.125 MB ⇒ 极便宜。"
echo "  设计：三臂只差**一个**因素，用于把 C1–C6 的机制逐条落实"
echo "    a) `c6_b4f32`：B=4 + 周期播种 + f32   ← 与 b4/ps_b* 可比（单变量：只加 f32）"
echo "    b) `c6_b8f32`：B=8 + 周期播种 + f32   ← 看 f32 是否改变 B=8 的结论"
nohup $PY -u _r537_parrun.py 2 _r555_c6cfg.json > _w2_r555_par.log 2>&1 < /dev/null &
echo "  已启动 `_r555`（2 并发 × 各 4 线程）"
