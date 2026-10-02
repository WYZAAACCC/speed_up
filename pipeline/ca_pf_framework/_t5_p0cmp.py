#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_p0cmp.py --- 第 8 条**决定性**一步：直接对比两臂检查点里的 `f3_pos_p0_m`

## 逻辑（**判据预先写死**）
`f3_pos_dx = (pm − P0)/dx`。
* **若两臂的 `P0` 相同** ⇒ 差异来自 `pm` ⇒ **是真实分叉**（求解器/几何真的不同）；
* **若两臂的 `P0` 不同** ⇒ 差异**至少部分**来自基准 ⇒ `f3_pos_dx` 列**不可比**，
  但**不能**据此说"没分叉" —— 还要看 `pm` 本身（而 `pm` 可由 `f3_pos_dx` 与 `P0` 反解）。
"""
import glob
import os

import numpy as np


def get(d):
    fs = sorted(glob.glob(os.path.join(d, '*.npz')))
    if not fs:
        return None, None
    f = fs[-1]
    with np.load(f, allow_pickle=False) as z:
        p0 = float(np.asarray(z['f3_pos_p0_m']).ravel()[0]) if 'f3_pos_p0_m' in z.files else None
        st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        L = float(np.asarray(z['L']).ravel()[0]) if 'L' in z.files else 0.0
        N = int(np.asarray(z['N']).ravel()[0]) if 'N' in z.files else 0
    return dict(f=os.path.basename(f), p0=p0, step=st, dx=(L / N if N else 0.0)), p0


A, pa = get('_exp/_bk_t5/dry_ck8A/ckpt')      # 续跑臂
B, pb = get('_exp/_bk_t5/dry_ck8B/ckpt')      # 一次跑完臂
print('=' * 96)
print('第 8 条决定性一步：两臂检查点的 `f3_pos_p0_m`')
print('=' * 96)
for nm, d in (('A（续跑）', A), ('B（一次跑完）', B)):
    if d is None:
        print('  %-12s ⚠ 无检查点' % nm)
    else:
        print('  %-12s 帧=%-14s step=%-4d  dx=%.4g m   **P0 = %.10g m**（= %.4f Δx）'
              % (nm, d['f'], d['step'], d['dx'], d['p0'], d['p0'] / d['dx']))
print()
if A and B:
    dP0 = A['p0'] - B['p0']
    print('  ★ ΔP0 = **%.6e m** = **%.6f Δx**' % (dP0, dP0 / A['dx']))
    # 由 series 里的 f3_pos_dx 与各自的 P0 反解 pm
    import csv
    def dxcol(t):
        p = '_exp/_bk_t5/dry_%s/series.csv' % t
        if not os.path.exists(p):
            return None
        r = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        for x in r:
            if x['step'] == '40':
                return (x.get('f3_pos_dx') or '').strip()
        return None
    va, vb = dxcol('ck8A'), dxcol('ck8B')
    print('  ★ series 的 `f3_pos_dx` @ step40：A = %s   B = %s' % (va, vb))
    print()
    print('  ── 判读 ──')
    if abs(dP0) < 1e-15:
        print('  **P0 完全相同** ⇒ `f3_pos_dx` 的差异**不是**基准造成的 ⇒ **是真实分叉** ❌')
    else:
        print('  **P0 不同**（差 %.6f Δx）⇒ `f3_pos_dx` 列**不可比**。' % (dP0 / A['dx']))
        print('  ⇒ 但它**只是**把差异归因到基准；**仍须**用**不含基准的物理量**判是否分叉。')
print('=' * 96)
