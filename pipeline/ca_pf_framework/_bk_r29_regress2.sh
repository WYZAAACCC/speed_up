#!/bin/bash
# _bk_r29_regress2.sh —— R29 **第二次**回归：在加了 `cfl_used` 列与 `--closed` 之后，
# 再次证明**归档默认路径逐位不变**。
#   （`_bk_r29_regress.sh` 那次跑在 `cfl_used` / `--closed` 之前 ⇒ 必须重跑。）
# `windowB_surface.py`（引擎）本轮**没改过** ⇒ 引擎恒等性不需要重跑，但一并跑一次更省心。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_r29_regress2.log
: > "$LOG"
{
  echo "################ ① 归档默认路径重跑（tag=def3）"
  "$PY" -u _bk_exp.py --N 96 --dx-nm 62.5 --steps 200 --every 10 --snap-every 50 \
    --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 \
    --tag def3 --out _exp/_bk_eng 2>&1 | tail -4
  echo
  echo "################ ①b 与归档 eng12 逐位比较（忽略 wall_s）"
  "$PY" -u _bk_defcheck.py def3 2>&1 | tail -6
  echo
  echo "################ ② 量具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -2
  echo
  echo "################ ③ 闭环文档数字 vs 代码"
  "$PY" _bk_docnum.py 2>&1 | tail -3
  echo
  echo "################ ④ 闭式自检"
  "$PY" windowB_closure.py 2>&1 | tail -2
} >> "$LOG" 2>&1
echo "=== REGRESS2 DONE $(date '+%F %T') ===" >> "$LOG"
