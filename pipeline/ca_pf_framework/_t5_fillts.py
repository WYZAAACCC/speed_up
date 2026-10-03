#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fillts.py --- "带延伸的场"的**时间序列**：它何时出现？（判据⑥ 的涌现证据）

## 判据（**预先写死**）
**对每个 band 快照，算每场的充填率 `fill = 胞数/包围盒体积`，并按 `fill` 分两类：**
* **紧凑**：`fill >= 0.10`
* **带延伸**：`fill < 0.10`
**⇒ 观察"带延伸"的场数随时间的变化：**
| 观察 | 结论 |
|---|---|
| **从 0 开始单调增长** | ⇒ **涌现**（早期没有、后来出现）⇒ 判据⑥ 的正面证据 |
| **一开始就有** | ⇒ 是**构造/早期形核**带来的，**不是涌现**（须记账）|
"""
import glob
import numpy as np

D = '_exp/_bk_t5/dry_t5H3'
DX, THR = 62.5, 0.10
snaps = []
for s in sorted(glob.glob(D + '/snap_*.npz')):
    try:
        with np.load(s, allow_pickle=False) as z:
            if 'band_fld' in z.files:
                snaps.append(s)
    except Exception:
        pass

print('=' * 92)
print('★ "带延伸的场"的时间序列（充填率 < %.2f 判为带延伸）' % THR)
print('=' * 92)
print('  %-8s %6s %8s %8s   %s' % ('step', '场数', '紧凑', '带延伸', '带延伸的场（编号）'))
print('  ' + '-' * 80)
for s in snaps:
    step = s.split('snap_')[-1].replace('.npz', '')
    with np.load(s, allow_pickle=False) as z:
        fld = np.asarray(z['band_fld']).ravel()
        bidx = np.asarray(z['band_idx']).ravel()
        reg = np.asarray(z['region'])
    coords = np.unravel_index(bidx.astype(np.int64), reg.shape)
    reg_at = reg[coords]
    tight, ext = [], []
    for f in sorted(set(int(x) for x in np.unique(fld).tolist())):
        if f == 0:
            continue
        sel = (fld == f) & (reg_at > 0)
        if not sel.any():
            continue
        cc = np.stack([c[sel] for c in coords], axis=1)
        lo, hi = cc.min(0), cc.max(0)
        vol = int(np.prod(hi - lo + 1))
        fill = float(sel.sum()) / max(vol, 1)
        (tight if fill >= THR else ext).append(f)
    print('  %-8s %6d %8d %8d   %s' %
          (step, len(tight) + len(ext), len(tight), len(ext), ext or '（无）'))

print()
print('  ── 判读（预先写死）──')
print('  若"带延伸"从 0 开始增长 ⇒ **涌现**（判据⑥ 的正面证据）；')
print('  若一开始就有        ⇒ 是构造/早期形核带来的，**不是涌现**（须记账）。')
