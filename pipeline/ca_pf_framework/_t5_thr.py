#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_thr.py --- §149.4 待查 1：step 800 的充填率分布（判"0→8 突跳"是否阈值假象）

## 判据（**预先写死**）
* 若 step 800 有多场的充填率落在 **0.10–0.12**（贴着阈值 0.10）⇒ **突跳**部分是阈值假象**；
* 若 step 800 各场充填率**普遍 ≥0.13**（离阈值远）⇒ **是真变化**（200 步内真的发生了形貌改变）。
"""
import numpy as np

DX = 62.5
THR = 0.10
for step in ('00800', '01000'):
    P = '_exp/_bk_t5/dry_t5H3/snap_%s.npz' % step
    with np.load(P, allow_pickle=False) as z:
        fld = np.asarray(z['band_fld']).ravel()
        bidx = np.asarray(z['band_idx']).ravel()
        reg = np.asarray(z['region'])
    coords = np.unravel_index(bidx.astype(np.int64), reg.shape)
    reg_at = reg[coords]
    rows = []
    for f in sorted(set(int(x) for x in np.unique(fld).tolist())):
        if f == 0:
            continue
        sel = (fld == f) & (reg_at > 0)
        if not sel.any():
            continue
        cc = np.stack([c[sel] for c in coords], axis=1)
        lo, hi = cc.min(0), cc.max(0)
        vol = int(np.prod(hi - lo + 1))
        rows.append((f, float(sel.sum()) / max(vol, 1)))
    fs = np.array([r[1] for r in rows])
    print('=' * 76)
    print('★ step %s：%d 个场   充填率 min=%.3f  p25=%.3f  中位=%.3f  max=%.3f'
          % (step, len(rows), fs.min(), float(np.percentile(fs, 25)),
             float(np.median(fs)), fs.max()))
    print('=' * 76)
    print('  ' + '  '.join('%d:%.3f' % r for r in rows))
    near = [f for f, v in rows if THR <= v < 0.12]
    print('  ⚠ 落在 [0.10, 0.12)（贴阈值）的场 = %s' % (near or '（无）'))
    print()

print('  ── 判读（预先写死）──')
print('  若 step 800 有多场贴阈值 ⇒ 突跳**部分是阈值假象**；')
print('  若 step 800 普遍 >=0.13（离阈值远）⇒ **是真变化**。')
