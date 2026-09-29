#!/bin/bash
# 计时标定：N=96 的引擎路径每步成本。只用来给后续长跑做预算；不产生任何结论。
# ⚠ 教训：`--snap-every 0` 会 ZeroDivisionError（`it % snap_every`），必须给非零。
# ⚠ 教训：本文件**只能用 write 工具生成**。用 PowerShell 的 Set-Content 改会写成
#    UTF-16/CRLF，之后 read 工具直接报 invalid UTF-8（AGENTS.md §3.9 同类坑）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
PY=/root/miniconda3/envs/ml/bin/python
LOG=_w2_bk_timing.log
: > "$LOG"
{
  echo "=== T-A: 60 步，无事件（cadence 很大）—— 纯推进成本 ==="
  /usr/bin/time -f "WALL %e s  MAXRSS %M KB" "$PY" -u _bk_exp.py \
    --N 96 --dx-nm 62.5 --steps 60 --every 60 --snap-every 60 \
    --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 9999 --nuc-overlap-nm 62.5 \
    --tag t60 --out _exp/_bk_time 2>&1 | tail -6
  echo "=== T-B: 60 步，含 1 次形核事件 @30 ==="
  /usr/bin/time -f "WALL %e s  MAXRSS %M KB" "$PY" -u _bk_exp.py \
    --N 96 --dx-nm 62.5 --steps 60 --every 60 --snap-every 60 \
    --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 \
    --tag t60e --out _exp/_bk_time 2>&1 | tail -6
} >> "$LOG" 2>&1
echo "=== DONE ===" >> "$LOG"
