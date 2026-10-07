#!/usr/bin/env python3
"""R53: 用 **v2 口径**（φ=0 零交叉 + 限定该场占优区）重测 `dry_mb1s62` 的面速率。

依据：`_r53_faces.py` 的正对照已过 —— **速率的恢复误差 <0.5%**，
绝对跨度带一个**常数偏置 ≈ +0.6·Δx**（⇒ 只报速率，不报绝对尺寸）。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
from _r53_faces import face_extent  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_mb1s62'
snaps = sorted(glob.glob(os.path.join(D, 'snap_*.npz')))
print('臂 %s  快照 %d' % (D, len(snaps)))
print()
print('  %-6s %-11s %-11s %-11s %-9s %s'
      % ('step', 'a (nm)', 'w (nm)', 'n (nm)', '交叉点', '场'))
rec = []
for s in snaps:
    z = np.load(s)
    if 'band_idx' not in z.files:
        continue
    N = int(z['N'])
    dx = float(z['L']) / N
    axes = dict(a=np.asarray(z['a_ax'], float),
                w=np.asarray(z['w_ax'], float),
                n=np.asarray(z['n_hab'], float))
    reg = z['region']
    idx, val, fld = z['band_idx'], z['band_val'], z['band_fld']
    # 逐场：只在"该场占优"的胞上收交叉点
    agg = {}
    ncross = 0
    for k in np.unique(fld):
        k = int(k)
        if k == 0:
            continue
        sel = (fld == k)
        phi = np.full((N, N, N), np.nan, np.float32)
        phi.ravel()[idx[sel]] = val[sel]
        if not np.isfinite(phi).any():
            continue
        e = face_extent(phi, (reg == k), dx, axes)
        for nm, v in e.items():
            agg.setdefault(nm, []).append(v)
    if not agg:
        continue
    row = dict(step=int(z['step']))
    for nm in ('a', 'w', 'n'):
        # 取**各场的中位数**（与旧口径的"中位"精神一致，但底层量换成了零交叉）
        row[nm] = float(np.median(agg[nm])) * 1e9 if nm in agg else float('nan')
    rec.append(row)
    print('  %-6d %-11.0f %-11.0f %-11.0f %-9s %d'
          % (row['step'], row['a'], row['w'], row['n'], '-', len(agg.get('a', []))))
if len(rec) < 3:
    print('⚠ 有效点不足')
    raise SystemExit(1)
print()
print('=== 分段速率（**v2 口径**，nm/步；正对照已证速率恢复误差 <0.5%）')
print('  %-14s %-12s %-12s %-12s %s'
      % ('窗口', 'd(a)', 'd(w)', 'd(n)', '判词'))
for lo, hi in ((0, 500), (500, 1000), (1000, 1500), (0, 10 ** 9)):
    seg = [r for r in rec if lo <= r['step'] <= hi]
    if len(seg) < 3:
        continue
    xs = np.array([r['step'] for r in seg], float)
    out = []
    for nm in ('a', 'w', 'n'):
        ys = np.array([r[nm] for r in seg], float)
        m = np.isfinite(ys)
        out.append(float(np.polyfit(xs[m], ys[m], 1)[0]) if m.sum() >= 3
                   else float('nan'))
    lab = '全程' if hi > 10 ** 8 else '%d–%d' % (lo, hi)
    verdict = ('**a 快**（拉长）' if out[0] > out[1]
               else '**w 快**（肥化）' if out[1] > out[0] else '相等')
    print('  %-14s %+-12.3f %+-12.3f %+-12.3f %s'
          % (lab, out[0], out[1], out[2], verdict))
