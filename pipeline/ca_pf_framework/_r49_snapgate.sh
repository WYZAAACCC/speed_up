#!/bin/bash
# R49 正对照：`--snap-every` 现在必须**独立**生效。
#   `--every 50 --snap-every 40 --steps 120`
#   期望 CSV 行 step: 0,50,100,120
#   期望快照  step: 0,40,80,120      ← 旧代码只会给 0,100,120（lcm(50,40)=200>120）
# 这是**修复的正对照**（AGENTS.md §3 教训 19：测具/改动都要先拿已知答案跑通）。
set -u
cd /mnt/f/speed_up/pipeline/ca_pf_framework || exit 1
PY=/root/miniconda3/envs/ml/bin/python
export MALLOC_MMAP_THRESHOLD_=65536 MALLOC_TRIM_THRESHOLD_=65536 MALLOC_ARENA_MAX=2 PYTHONDONTWRITEBYTECODE=1
TAG=r49cad
DIR="_exp/_bk_mb/dry_$TAG"          # ⚠ 目录名是 <arm>_<tag>，不是 <tag>
rm -rf "$DIR"
"$PY" -u _bk_exp.py --arm dry --N 32 --dx-nm 125 --laths 1,1 \
  --plate-L 400 --plate-W 200 --plate-T 635 --plate-t-physical 510 \
  --gamma0 0.25 --beta-h 6.477 --norm-smooth 0 --reinit-dt 1e-4 \
  --steps 120 --every 50 --snap-every 40 --pair-every 50 --nthreads 2 \
  --tag "$TAG" --out _exp/_bk_mb > "_w2_${TAG}.log" 2>&1
rc=$?
echo "=== exit rc=$rc"
"$PY" - "$TAG" <<'PY'
import sys, os, glob, re, csv
tag = sys.argv[1]
d = os.path.join('_exp/_bk_mb', 'dry_' + tag)
snaps = sorted(int(re.search(r'snap_(\d+)', s).group(1))
               for s in glob.glob(os.path.join(d, 'snap_*.npz')))
rows = []
with open(os.path.join(d, 'series.csv')) as f:
    for r in csv.DictReader(f):
        rows.append(int(r['step']))
print('CSV   steps =', rows)
print('snap  steps =', snaps)
ok_csv = rows == [0, 50, 100, 120]
ok_snap = snaps == [0, 40, 80, 120]
print('CSV 行命中 every 门          :', 'PASS' if ok_csv else 'FAIL')
print('快照独立于 every 门（修复生效）:', 'PASS' if ok_snap else 'FAIL')
# 额外：独立快照必须带 region 且带内 φ
import numpy as np
z = np.load(os.path.join(d, 'snap_00040.npz'))
keys = sorted(z.files)
print('snap_00040 keys =', keys)
print('  region shape/dtype =', z['region'].shape, z['region'].dtype)
band = [k for k in keys if k.startswith('b_') or 'band' in k or k.startswith('phi_')]
print('  带内 φ 相关键 =', band[:6], '...' if len(band) > 6 else '')
print('VERDICT =', 'PASS' if (ok_csv and ok_snap) else 'FAIL')
PY
