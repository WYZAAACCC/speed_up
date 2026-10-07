#!/usr/bin/env bash
# _r544b_relaunch.sh —— 归档 `_r544` 的失败产物（**不删除**）并重启周期播种 A/B
set -u
cd "$(dirname "$0")"
PY=/root/miniconda3/envs/ml/bin/python
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

mkdir -p _exp/_superseded
for d in ps_b8 ps_b3; do
  if [ -d "_exp/_bk_par/$d" ]; then
    mv "_exp/_bk_par/$d" "_exp/_superseded/r544bfail_$d"
    echo "已归档（改名不删）: _exp/_superseded/r544bfail_$d"
  fi
done

nohup $PY -u _r537_parrun.py 2 _r544_pscfg.json > _w2_r544b_par.log 2>&1 < /dev/null &
echo "已启动周期播种 A/B（2 并发 × 各 4 线程）"
