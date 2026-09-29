#!/usr/bin/env bash
# _r30_runall.sh —— R30 审计：把全部对照跑一遍并把输出汇总到 _r30_audit_out.txt
# 环境纪律：单进程 ≤4 线程；每一段都短（≤3 min）。不碰别人的长跑。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536
export MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
PY=/root/miniconda3/envs/ml/bin/python
OUT=_r30_audit_out.txt
: > "$OUT"

run () {
  echo "" >> "$OUT"
  echo "############################################################################" >> "$OUT"
  echo "### $*" >> "$OUT"
  echo "### 时间: $(date '+%F %T')" >> "$OUT"
  echo "############################################################################" >> "$OUT"
  timeout 400 $PY -u "$@" >> "$OUT" 2>&1
  echo "### exit=$?" >> "$OUT"
}

run _bk_measure.py --selftest
run _r1_exp.py --selftest
run _r30_ctl_measure.py
run _r30_ctl_column.py
run _r30_ctl_cfl.py
run _r30_units.py
run _r30_repro.py
run _r30_gapw.py
run _r30_probe_sha.py
run _bk_cfl.py
echo "完成：$OUT"
