#!/bin/bash
# _r30_regress.sh —— R30 改动的**回归**：证明"加了新列 + 自适应柱半径"之后
#   **归档默认路径的动力学与旧量具口径逐位不变**。
#
# 为什么必须跑：R30 改了 `_bk_measure.measure_state`（新增 `nslab_n1`/`runs1`/
#   `nf3_col1`/`r_col_nm`/`col_cover_*`）与 `_bk_exp.py` 的 `COLS`。
#   按本仓库纪律（`R8`）：**凡改动引用路径，必须留逐位回归**。
#
# 判据（预先写死）：
#   G-1 与归档 `eng12` 的**共有列**逐位一致（忽略 wall_s）
#   G-2 新列存在且非空（`nslab_n1`/`runs1`/`nf3_col1`/`r_col_nm`/`col_cover_min`）
#   G-3 量具自检 `_bk_measure.py --selftest` FAIL=0
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
LOG=_w2_r30_regress.log
: > "$LOG"
{
  echo "################ ① 归档默认路径重跑（tag=r30reg）  $(date '+%F %T')"
  "$PY" -u _bk_exp.py --N 96 --dx-nm 62.5 --steps 200 --every 10 --snap-every 50 \
    --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 \
    --tag r30reg --out _exp/_bk_eng 2>&1 | tail -4
  echo
  echo "################ ①b 与归档 eng12 逐位比较（忽略 wall_s）"
  "$PY" -u _bk_defcheck.py r30reg 2>&1 | tail -8
  echo
  echo "################ ② 新列非空核对"
  "$PY" -u _r30_csv.py _exp/_bk_eng/dry_r30reg/series.csv \
      step,nslab_n,nslab_n1,nf3_col,nf3_col1,r_col_nm,col_cover_min 2>&1 | tail -6
  echo
  echo "################ ③ 量具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -3
} >> "$LOG" 2>&1
echo "=== R30 REGRESS DONE $(date '+%F %T') ===" >> "$LOG"
tail -30 "$LOG"
