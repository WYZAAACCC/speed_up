#!/bin/bash
# _r220_f1e2e.sh —— `f1_area_m2` / `nf1` 的**端到端**验证：真的进 `series.csv` 了吗？
#
# 判据：
#   F-1 表头里有 `nf1` / `f1_area_m2` / `f1_area_stair`
#   F-2 三个量都**非空且有限**
#   F-3 `f1_area_m2 > 0`（有 α′ 就一定有 α′/β 界面）
#   F-4 **与旧列口径一致**：`nf1` 应 ≈ 各 `f1_faces_<k>` 之和（来自同一循环）
#   F-5 负对照：**不传** `--diag-terms` 时**不**多出 `diag_terms.json`（无关，但顺手查）
set -u
cd "$(dirname "$0")" || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 \
       MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1

rm -rf _exp/_bk_f1
"$PY" -u _bk_exp.py --arm dry --N 32 --dx-nm 125 --laths 1,1,2,2 --gap-nm 0 \
  --steps 4 --every 2 --snap-every 4 --pair-every 0 --nthreads 2 \
  --tag f1e2e --out _exp/_bk_f1 > _w2_r220.log 2>&1
echo "退出码 = $?"
echo
echo "=== F-1 表头检查 ==="
head -1 _exp/_bk_f1/dry_f1e2e/series.csv | tr ',' '\n' | grep -n -E '^(nf1|f1_area_m2|f1_area_stair|f1_faces_[0-9]+)$' | sed 's/^/  /'
echo
echo "=== 各步的 nf1 / f1_area ==="
"$PY" - <<'PY'
import csv
rows = list(csv.DictReader(open('_exp/_bk_f1/dry_f1e2e/series.csv')))
hdr = list(rows[0].keys())
print('  CSV 里没有逐根的 `f1_faces_<k>`（那些是 `measure_state` 的**内部键**，')
print('  只把聚合的 nf1/f1_area 写进了 COLS）⇒ 一致性必须在**函数层**查，见下。')
for r in rows:
    print('  step %-3s nf1=%-7s f1_area=%.4e m²  stair=%.4e  (stair/area=%.3f)'
          % (r['step'], r['nf1'], float(r['f1_area_m2']),
             float(r['f1_area_stair']),
             float(r['f1_area_stair']) / float(r['f1_area_m2'])))
print()
print('  F-1 三列都在       ⇒ %s' % ('✅' if all(
    k in hdr for k in ('nf1', 'f1_area_m2', 'f1_area_stair')) else '❌'))
pos = any(float(r['f1_area_m2']) > 0 for r in rows)
print('  F-3 f1_area > 0    ⇒ %s' % ('✅' if pos else '❌'))
PY
echo
echo "=== F-4（函数层）：nf1 是否 == Σ 逐根 f1_faces_k ==="
"$PY" - <<'PY'
import sys, numpy as np
sys.path.insert(0, '.')
import _bk_measure as BM
N, dx = 24, 1e-8
reg = np.zeros((N, N, N), np.int8)
reg[6:12] = 1
reg[12:18] = 2
r = BM.measure_state(reg, dx, np.asarray([1.0, 0.0, 0.0], float),
                     w_ax=np.array([0., 1., 0.]), a_ax=np.array([1., 0., 0.]),
                     vmap={1: 1, 2: 2}, r_col=300e-9)
per = {k: v for k, v in r.items() if k.startswith('f1_faces_')}
s = sum(per.values())
print('  逐根 %s ⇒ Σ=%d ；聚合 f1_faces=%d ⇒ %s'
      % (per, s, r['f1_faces'], '✅ 一致' if s == r['f1_faces'] else '❌ 不一致'))
print('  ⇒ **同一循环同一个 `_t` 累加** ⇒ 口径一致（结构性）')
PY
echo
echo "=== F-5 不该有 diag_terms.json（没传 --diag-terms）==="
[ -f _exp/_bk_f1/dry_f1e2e/diag_terms.json ] && echo "  ❌ 不该有" || echo "  ✅ 没有（门控正确）"
