#!/bin/bash
# R49 正对照（`v_by_face`）：`<M(n)·dG>_面 · dt` 必须落盘、非空、且量级合理。
#   已知答案（可独立算出来，不依赖引擎）：
#     ① 面上任一点的速度 ≤ 0.15Δx/步（CFL 就是按全域最大胞定的）⇒ `v_*_nabs ≤ 18.75`
#     ② `v_tip_nabs` 必须与"用中位 dG 从外面算的那个数"同量级（0.26 nm/步）
#     ③ `n` 必须 > 0（面分类没退化）
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
TAG=r49vb
DIR="_exp/_bk_mb/dry_$TAG"
rm -rf "$DIR"
"$PY" -u _bk_exp.py --arm dry --N 48 --dx-nm 125 --laths 1,1 \
  --plate-L 1600 --plate-W 700 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 200 --every 20 --snap-every 20 --pair-every 40 --nthreads 2 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_${TAG}.log" 2>&1
echo "=== exit rc=$?"
"$PY" - "$DIR" <<'PY'
import csv, os, sys
d = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(d, 'series.csv'))))
cols = ['step', 'v_tip_nsgn', 'v_tip_nabs', 'v_side_nsgn', 'v_side_nabs',
        'v_wide_nabs', 'dG_tip', 'dG_tip_p90']
print('%-6s %-11s %-11s %-11s %-11s %-11s %-12s %s' % tuple(cols))
for r in rows:
    print('%-6s %-11s %-11s %-11s %-11s %-11s %-12s %s'
          % tuple(r.get(c, '(缺)') for c in cols))
CFL = 0.15 * 125.0
ok = True
tail = [r for r in rows if r.get('v_tip_nabs') not in (None, '')]
if not tail:
    print('FAIL: v_tip_nabs 全程为空 ⇒ 接线没通')
    ok = False
else:
    v = [float(r['v_tip_nabs']) for r in tail]
    vs = [float(r['v_side_nabs']) for r in tail if r.get('v_side_nabs') not in (None, '')]
    vw = [float(r['v_wide_nabs']) for r in tail if r.get('v_wide_nabs') not in (None, '')]
    print()
    print('CFL 上限 0.15Δx = %.2f nm/步' % CFL)
    print('tip  |v| 平均: %.4f … %.4f nm/步' % (v[0], v[-1]))
    if vs:
        print('side |v| 平均: %.4f … %.4f nm/步' % (vs[0], vs[-1]))
    if vw:
        print('wide |v| 平均: %.4f … %.4f nm/步' % (vw[0], vw[-1]))
    print('① 全部 ≤ CFL 上限 :', 'PASS' if all(x <= CFL + 1e-9 for x in v + vs + vw) else 'FAIL')
    print('② tip 末值与外面算的 0.26 nm/步 同量级 :',
          'PASS' if 0.02 <= v[-1] <= 3.0 else 'FAIL(%.4f)' % v[-1])
    print('③ 三档都非空 :', 'PASS' if (v and vs and vw) else 'FAIL')
    ok = ok and all(x <= CFL + 1e-9 for x in v + vs + vw) and 0.02 <= v[-1] <= 3.0
print('VERDICT =', 'PASS' if ok else 'FAIL')
PY
