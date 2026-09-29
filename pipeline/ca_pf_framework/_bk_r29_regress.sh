#!/bin/bash
# _bk_r29_regress.sh —— R29 的**回归**：改完 `_bk_exp.py` 后必须证明默认路径没变。
#   ① 用最简命令行重跑一次（tag=def2），与归档的 eng12 **逐位**比较；
#   ② 引擎恒等性 `_bk_nuc_identity.py`（U-1..U-4 + 7 条对照）；
#   ③ 量具自检 `_bk_measure.py --selftest`。
# 三条全过才允许跑新的闭环算例。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
LOG=_w2_bk_r29_regress.log
: > "$LOG"
{
  echo "################ ① 默认路径重跑（最简命令行）"
  "$PY" -u _bk_exp.py --N 96 --dx-nm 62.5 --steps 200 --every 10 --snap-every 50 \
    --pair-every 10 --norm-smooth 0 --nthreads 2 --reinit-dt 1e-4 \
    --grow-stack --eng-cadence 30 --nuc-overlap-nm 62.5 \
    --tag def2 --out _exp/_bk_eng 2>&1 | tail -4
  echo
  echo "################ ①b 与 eng12 逐位比较"
  "$PY" - <<'PYEOF'
import csv, os
HERE = os.path.dirname(os.path.abspath('_bk_exp.py'))
def load(tag):
    return list(csv.DictReader(open(os.path.join('_exp/_bk_eng', tag, 'series.csv'))))
a, b = load('eng_eng12'), load('dry_def2')
print('行数: eng12=%d  def2=%d' % (len(a), len(b)))
bad = []
for i, (x, y) in enumerate(zip(a, b)):
    for k in x:
        if k == 'wall_s':
            continue
        if x[k] != y[k]:
            bad.append((i, k, x[k], y[k]))
print('逐位比较（忽略 wall_s）：差异字段数 = %d' % len(bad))
for t in bad[:10]:
    print('   step=%s  %s: eng12=%r  def2=%r' % (a[t[0]]['step'], t[1], t[2], t[3]))
print('⇒ %s' % ('**逐位一致**' if not bad else '**有差异**'))
PYEOF
  echo
  echo "################ ② 引擎恒等性"
  "$PY" -u _bk_nuc_identity.py 2>&1 | grep -E '^  U-|FAIL ='
  echo
  echo "################ ③ 量具自检"
  "$PY" _bk_measure.py --selftest 2>&1 | tail -3
} >> "$LOG" 2>&1
echo "=== REGRESS DONE ===" >> "$LOG"
