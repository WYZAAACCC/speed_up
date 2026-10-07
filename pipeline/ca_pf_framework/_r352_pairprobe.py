#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r352_pairprobe.py —— ★★ E-2：为什么**异变体**邻居会被母相场挤掉，而同变体不会？

## 已知（`§170`，两条都是实测）

| 事实 | 数值 |
|---|---|
| `advance` 的 `(karr,larr)` 基里 **F2（异变体）胞数** | **≡ 0**（400/400 步） |
| `advance` 的 `(karr,larr)` 基里 **F3（同变体）胞数** | ≈ **1521** |
| `region` 基的几何 F2 面数（同一批数据） | **1922**（step 400） |

而 `argmin2`（`windowB_par.py:217-225`）的亚军判据是 **`pj < best` 严格比较**、
`j` 从 0 扫起 ⇒ **并列时编号小的赢（母相 `j=0` 最先）**。

## 假设（**待检验**）

> **母相场 `φ_0` 在变体内部有"幽灵负值"**（`§168.3` 实测幽灵负区 0% → 8–13%）
> ⇒ 在 F2 界面胞上 `φ_0 < φ_l` ⇒ **亚军被 `j=0` 拿走**；
> 而在 F3 界面胞上，同变体的**复制场** `φ_{k'}` 比 `φ_0` **更负** ⇒ 亚军是 `k'` ⇒ F3 正常。

## 判据（**先写死**）

* **W-0 口径自证**：在被考察的胞上，"三个场的 `argmin` == 归档 `region`" 必须成立
  （否则我的稀疏 φ 读数不可用 —— 硬规则 ④/㊹）。
* **W-1**：F2 胞上 **`φ_0` 存下来且为负**的占比 ⇒ 假设的直接证据。
* **W-2 对照**：同一口径在 **F3** 胞上 ⇒ `φ_{k'}`（同变体复制场）**比 `φ_0` 更负**的占比。
* **W-3**：**若 W-1 与 W-2 给出相反模式 ⇒ 假设成立**；若两者同向 ⇒ **假设作废**，
  必须另找机制（不得硬套）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def main():
    print('=' * 104)
    print('_r352 —— E-2：异变体邻居为什么被母相场挤掉？（稀疏 φ 直读）')
    print('=' * 104)
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    snap = sys.argv[2] if len(sys.argv) > 2 else ''
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    if not fs:
        print('  ⚠ 无快照'); return 2
    f = os.path.join(d, snap) if snap else fs[-1]
    z = np.load(f, allow_pickle=True)
    N = int(z['N'])
    reg = np.asarray(z['region'], np.int64)
    vk = np.asarray(z['vmap_keys'], np.int64)
    vv = np.asarray(z['vmap_vals'], np.int64)
    nf = int(z['band_fld'].max()) + 1
    var = np.full(nf, -1, np.int64)
    var[vk] = vv
    p = rebuild(z)
    fin = np.isfinite(p)
    B = int(z['band_cells'])
    dxx = 62.5e-9
    mf = os.path.join(d, 'meta.json')
    if os.path.exists(mf):
        dxx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
    print('  arm=%s  快照=%s  step=%s  N=%d  nf=%d  B=%d  Δx=%.3f nm'
          % (arm, os.path.basename(f), z['step'], N, nf, B, dxx * 1e9))

    # ---------------- 收界面（有向：a -> b） ----------------
    cls = {'F1': [], 'F2': [], 'F3': []}
    for ax in range(3):
        b = np.roll(reg, -1, axis=ax)
        sel = reg != b
        if not sel.any():
            continue
        I = np.where(sel)
        A = reg[I]
        Bv = b[I]
        va = var[np.clip(A, 0, nf - 1)]
        vb = var[np.clip(Bv, 0, nf - 1)]
        both = (va > 0) & (vb > 0)
        keys = np.where(~both, 'F1', np.where(va != vb, 'F2', 'F3'))
        for kk in ('F1', 'F2', 'F3'):
            m = keys == kk
            if m.any():
                cls[kk].append(((I[0][m], I[1][m], I[2][m]), A[m], Bv[m]))
    print('  有向界面计数：F1=%d  F2=%d  F3=%d'
          % tuple(sum(c[1].size for c in cls[k]) for k in ('F1', 'F2', 'F3')))

    # ---------------- W-0..W-2 ----------------
    print()
    print('  %-4s %8s %10s %13s %13s %14s' %
          ('类', '胞数', 'W-0 自证', 'phi0存且<0', 'phi_b存且<0',
           'phi0<phi_b(⇒larr=0)'))
    for kk in ('F2', 'F3'):
        if not cls[kk]:
            print('  %-4s （无胞）' % kk)
            continue
        I = tuple(np.concatenate([c[0][j] for c in cls[kk]]) for j in range(3))
        A = np.concatenate([c[1] for c in cls[kk]])
        Bv = np.concatenate([c[2] for c in cls[kk]])
        n = A.size
        p0 = p[0][I]
        pa = p[A, I[0], I[1], I[2]]
        pb = p[Bv, I[0], I[1], I[2]]
        s0 = fin[0][I]
        sa = fin[A, I[0], I[1], I[2]]
        sb = fin[Bv, I[0], I[1], I[2]]
        # W-0：三场（0, a, b）的 argmin 是否 == a == region
        cand = np.stack([p0, pa, pb], 0)
        ok3 = s0 & sa & sb
        am = np.argmin(np.where(np.isnan(cand), np.inf, cand), 0)
        who = np.array([0, 0, 0])       # 占位，下面按行取
        w0 = float((np.where(am == 0, 0, np.where(am == 1, A, Bv)) == A)[ok3].mean()) \
            if ok3.any() else float('nan')
        f0neg = float((s0 & (p0 < 0)).sum()) / max(n, 1)
        fbneg = float((sb & (pb < 0)).sum()) / max(n, 1)
        cmp_ = s0 & sb & ~np.isnan(p0) & ~np.isnan(pb)
        lt = float(((p0 < pb)[cmp_]).sum()) / max(int(cmp_.sum()), 1)
        print('  %-4s %8d %10s %12.1f%% %12.1f%% %13.1f%%（可比 %d）'
              % (kk, n, ('%.4f' % w0) if w0 == w0 else '—',
                 100.0 * f0neg, 100.0 * fbneg, 100.0 * lt, int(cmp_.sum())))
    print()
    print('  ## 判据')
    print('  * **W-0** 必须 = 1.0000（否则稀疏 φ 读数不可用 ⇒ 全体作废）')
    print('  * **W-1**：F2 上 "phi0 存且<0" 占比高 ⇒ 母相幽灵负值把亚军抢走')
    print('  * **W-2 对照**：F3 上 "phi_b 存且<0" 应更高（同变体复制场的幽灵更深）')
    print('  * **W-3**：F2 与 F3 模式相反 ⇒ 假设成立；同向 ⇒ **假设作废，另找机制**')
    print()
    print('  ⚠ 记账：`band_*` 只存 `|φ|≤BΔx` ⇒ "没存"**不等于**"值不存在"（硬规则 ㊳）；')
    print('     本表只统计**存下来**的那部分，占比的分母是**全部该类胞**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
