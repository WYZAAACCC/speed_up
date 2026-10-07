#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r338_sdfgrad.py —— ★★ φ 还是**距离函数**吗？幽灵负区与界面法向的因果检验（`_r336` 的修正版）。

## `_r336` 的两处毛病（本轮自查错误 #31）

1. **G-3 被 NaN 污染**：幽灵胞上 winner 的 φ 常是 `+inf`（没存）⇒ `d = pha − phb` 出现
   `inf − inf = nan` ⇒ 中位变 `nan` ⇒ 判据在 `nan` 上比较，自动落到"无差别"分支。
   **判据在 nan 上比较**是硬规则 ㊱ 的同类错（不得让比较对象悄悄退化成另一个东西）。
2. **代理没标定**：G-1 实测 **0.8216**（不是 ≈1），而我**没有**先用一个已知答案标定
   `l`（第二小场）这个选择口径 —— 所以绝对值不能与代码记录的 0.70–0.93 相比。

## 本版怎么修

* 所有统计**先取有限值**（`np.isfinite`），并在表里打印**用到的胞数**；
  `nan` 一律显式记 `—`，不参与比较。
* 加一条**直接**的 SDF 判据（不依赖 `l` 的选择）：
  @@|\\nabla\\phi_k|@@ —— 单位距离函数必须 **= 1**。分别在
  **(A) 合法内部**（`region==k` 且 `φ_k<0`）与 **(B) 幽灵区**（`φ_k<0` 且 `region≠k`）上统计。

## 判据（**先写死**）

* **S-1 标定**：`step=0` 的 **(A) 组 |∇φ_k| 中位**必须 ≈ **1.0**
  （`_r335` 已证 t=0 时 φ 是**完美**多相 SDF ⇒ 这是"已知答案"）。
  **不过 ⇒ 本脚本全部作废。**
* **S-2 退化**：`step 0 → 末`，(A) 组 |∇φ_k| 中位从 ≈1 掉到多少？与幽灵数**同向**吗？
* **S-3 因果（决定性）**：末快照内，**界面胞**按「是否在幽灵的 2-胞邻域内」分两组，
  比较 @@|\\nabla d|@@ 中位（有限值口径）。**幽灵组显著更低 ⇒ 因果**；
  **无差别 ⇒ 幽灵不是原因，假设作废**。
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


def gmag(a, dx):
    with np.errstate(invalid='ignore'):
        return np.sqrt(sum(g ** 2 for g in np.gradient(a, dx, edge_order=2)))


def med_finite(v, m):
    """在掩码 m 上取**有限值**中位；返回 (中位, 用到的胞数)。"""
    mm = m & np.isfinite(v)
    n = int(mm.sum())
    return (float(np.median(v[mm])) if n else float('nan')), n


def analyze(z, dx):
    N = int(z['N'])
    reg = np.asarray(z['region'], np.int64)
    p = rebuild(z)
    nf = p.shape[0]
    fin = np.isfinite(p)
    kk = np.arange(nf)[:, None, None, None]
    ghost_f = fin & (p < 0.0) & (reg[None] != kk)
    legal_f = fin & (p < 0.0) & (reg[None] == kk)
    n_ghost = int(ghost_f.sum())
    # ---- A/B: |∇φ_k| ----
    gphi = np.stack([gmag(p[k].astype(np.float64), dx) for k in range(nf)], 0)
    A, nA = med_finite(gphi, legal_f)
    Bv, nB = med_finite(gphi, ghost_f)
    # ---- 界面胞与 d ----
    full = np.where(fin, p, np.inf)
    order = np.argsort(full, axis=0)
    w = reg
    l2 = order[1]
    l2 = np.where(l2 == w, order[2], l2)
    pha = np.take_along_axis(full, w[None], 0)[0]
    phb = np.take_along_axis(full, l2[None], 0)[0]
    d = pha - phb
    gd = gmag(d.astype(np.float64), dx)
    ghost_any = ghost_f.any(0)
    dil = ghost_any.copy()
    for _ in range(2):
        nx = dil.copy()
        for ax in range(3):
            nx |= np.roll(dil, 1, ax) | np.roll(dil, -1, ax)
        dil = nx
    interior = np.zeros((N, N, N), bool)
    interior[1:-1, 1:-1, 1:-1] = True
    iface = np.isfinite(d) & (np.abs(d) <= 1.0 * dx) & interior
    allv, nall = med_finite(gd, iface)
    near, nnear = med_finite(gd, iface & dil)
    far, nfar = med_finite(gd, iface & ~dil)
    return dict(n_ghost=n_ghost, nA=nA, A=A, nB=nB, B=Bv,
                nall=nall, allv=allv, nnear=nnear, near=near,
                nfar=nfar, far=far)


def main():
    print('=' * 112)
    print('_r338 —— φ 还是距离函数吗？（|∇φ_k| 直接判据 + 幽灵/界面法向因果检验）')
    print('=' * 112)
    arms = sys.argv[1:] or ['saSet2']
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
        dx = 62.5e-9
        mf = os.path.join(d, 'meta.json')
        if os.path.exists(mf):
            dx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
        print()
        print('  ### arm=%s  Δx=%.3f nm  快照 %d 张' % (arm, dx * 1e9, len(fs)))
        print('  %-6s %8s %10s %10s %10s %10s %10s %10s %10s' %
              ('step', 'n_ghost', 'A:|∇φ|内', 'nA', 'B:|∇φ|鬼', 'nB',
               '|∇d|全', '|∇d|近鬼', '|∇d|远鬼'))
        rows = []
        for f in fs:
            z = np.load(f, allow_pickle=True)
            if 'band_idx' not in z:
                continue
            r = analyze(z, dx)
            def fm(v, n):
                return ('%.4f(%d)' % (v, n)) if n else '—'
            print('  %-6s %8d %10s %10s %10s %10s %10s %10s %10s' %
                  (z['step'], r['n_ghost'],
                   fm(r['A'], r['nA']), '',
                   fm(r['B'], r['nB']), '',
                   fm(r['allv'], r['nall']), fm(r['near'], r['nnear']),
                   fm(r['far'], r['nfar'])))
            rows.append((int(z['step']), r))
        print()
        if rows:
            s0, r0 = rows[0]
            print('  **S-1 标定** step=%d：合法内部 |∇φ_k| 中位 = **%.4f**（用 %d 胞）%s'
                  % (s0, r0['A'], r0['nA'],
                     '✅ 标定通过' if abs(r0['A'] - 1.0) < 0.05 else '❌ 未标定 ⇒ 作废'))
            if not (abs(r0['A'] - 1.0) < 0.05):
                continue
            sl, rl = rows[-1]
            print('  **S-2 退化** step %d → %d：|∇φ_k| 内 **%.4f → %.4f**（%+.2f%%）；'
                  '幽灵 %d → %d'
                  % (s0, sl, r0['A'], rl['A'], 100.0 * (rl['A'] - r0['A']) / r0['A'],
                     r0['n_ghost'], rl['n_ghost']))
            print('              幽灵区 |∇φ_k| = %.4f（%d 胞）'
                  % (rl['B'], rl['nB']) if rl['nB'] else '              幽灵区 |∇φ_k| = —')
            if rl['nnear'] and rl['nfar']:
                a, b = rl['near'], rl['far']
                rel = 100.0 * (a - b) / b
                print('  **S-3 决定性** 末快照：近鬼 %d 胞 |∇d| = **%.4f**，远鬼 %d 胞 '
                      '= **%.4f**，相对差 **%+.2f%%**'
                      % (rl['nnear'], a, rl['nfar'], b, rel))
                if rel < -2.0:
                    print('      ⇒ ✅ 幽灵邻域的 |∇d| **显著更低** ⇒ 因果链成立')
                elif rel > 2.0:
                    print('      ⇒ ❌ **反了** ⇒ 假设作废')
                else:
                    print('      ⇒ ❌ **无差别**（|Δ| ≤ 2%）⇒ 幽灵**不是**原因，假设作废')
            else:
                print('  S-3：样本不足 ⇒ 不适用')
    print()
    print('  ⚠ 记账：`band_*` 只存 `|φ_k| ≤ BΔx` ⇒ 幽灵数是**下界**；')
    print('     `l` 取"存下来的第二小场"，与代码 `larr`（全局第二小）可能不同。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
