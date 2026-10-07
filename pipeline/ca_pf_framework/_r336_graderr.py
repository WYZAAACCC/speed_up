#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r336_graderr.py —— ★★ 「幽灵负区」是不是 `|∇d|` 中位只有 0.70–0.93 的原因？

## 由来

`_r335` 实测（`band_*` 稀疏 φ，6 条臂）：
* **step 0**：`φ_k<0` 而 `region≠k` 的胞 = **0**（φ 是**完美**的多相 SDF）；
* **step 20 → 400/600**：该比例 **0 → 8.2–13.2%**，且厚度从 `|φ|<1Δx` 长到 **2–6Δx**；
* `hard = 0` ⇒ `region` 与 `phi` **互相自洽**（不是存档顺序问题）。
⇒ 场的"内部"（负区）**随时间互相侵入**，φ **不再是距离函数**。

## 这条为什么可能牵动物理

`windowB_surface.py:3161` 的界面法向是
@@\\hat n \\propto \\nabla(\\phi_k-\\phi_l)@@（winner − loser，**这个写法本身对幽灵免疫**，
因为零集 `φ_k=φ_l` 就是界面）。但**模长**不免疫：代码自己的实测记录
（`:3166-3167`，`_probe_LT.py`）说带内 @@|\\nabla d|@@ 中位只有 **0.70–0.93**（应 ≈1）
⇒ 法向有散布 ⇒ 噪声抬高慢方向迁移率 ⇒ 各向异性对比被压缩
（设计 长:厚 = 33，实测只有 8.45）。

**假设（本脚本要证实/证伪）**：@@|\\nabla d|@@ 的退化与幽灵负区的增长**同步**。

## 判据（**先写死**）

* **G-1 正对照**：`step=0` 快照上，界面胞的 @@|\\nabla d|@@ 中位应 **≈ 1.0**
  （t=0 时 φ 是精确 SDF，且 `_r335` 实测零重叠）。
* **G-2 趋势**：同一条臂 `step = 0 → 末` 上，@@|\\nabla d|@@ 中位与幽灵胞数**同向变化**
  （都在恶化）⇒ 支持假设。
* **G-3 对照判据（这条才是决定性的）**：**同一张快照内**，
  把界面胞按「本胞 3×3×3 邻域里有没有"幽灵"（`φ_k<0 且 region≠k` 且存下来）」分两组，
  比较两组的 @@|\\nabla d|@@ 中位。**若幽灵组的 @@|\\nabla d|@@ 显著更低 ⇒ 因果链成立**；
  **若两组无差别 ⇒ 幽灵不是原因，假设作废**（不得拿 G-2 的"同向"当证据 —— 同向不是因果）。

⚠ 记账：`band_*` 只有 `|φ|≤6Δx` 的胞可见 ⇒ 幽灵数是**下界**；
   界面胞的 `l` 取"存下来的第二小场"，与代码的 `larr`（全局第二小）**可能不同**
   （带外看不见）。G-1 若 ≈1 说明这个代理够用。
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
DX = 62.5e-9


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def gradmag(a, dx):
    """与代码同口径的中心差分（`np.gradient(..., edge_order=2)`）。"""
    return np.sqrt(sum(g ** 2 for g in np.gradient(a, dx, edge_order=2)))


def analyze(z, dx):
    N = int(z['N'])
    B = int(z['band_cells'])
    reg = np.asarray(z['region'], np.int64)
    p = rebuild(z)
    nf = p.shape[0]
    fin = np.isfinite(p)
    # 幽灵掩码（逐场）
    kk = np.arange(nf)[:, None, None, None]
    ghost_f = fin & (p < 0.0) & (reg[None] != kk)
    n_ghost = int(ghost_f.sum())
    # 逐胞：本胞有没有幽灵
    ghost_any = ghost_f.any(0)
    # 逐胞：winner(region) 与 存下来的第二小
    full = np.where(fin, p, np.inf)
    order = np.argsort(full, axis=0)
    w = reg                                   # 真 winner（归档 region）
    l2 = order[1]                             # 存下来的第二小
    l2 = np.where(l2 == w, order[2], l2)      # 若第二小是 winner 自己，取第三小
    pha = np.take_along_axis(full, w[None], 0)[0]
    phb = np.take_along_axis(full, l2[None], 0)[0]
    d = pha - phb
    # 两个场都存下来了才算
    both = (np.take_along_axis(fin, w[None], 0)[0]) & \
           (np.take_along_axis(fin, l2[None], 0)[0])
    gd = gradmag(d, dx)
    # 界面胞：|d| ≤ 1Δx 且三向邻居都有限（gradmag 已要求内部点）
    iface = both & (np.abs(d) <= 1.0 * dx)
    interior_ok = np.zeros((N, N, N), bool)
    interior_ok[1:-1, 1:-1, 1:-1] = True
    iface = iface & interior_ok
    # 幽灵邻域（3×3×3 膨胀）
    gdil = ghost_any.copy()
    for ax in range(3):
        gdil |= np.roll(ghost_any, 1, ax) | np.roll(ghost_any, -1, ax)
    gdil2 = gdil.copy()
    for ax in range(3):
        gdil2 |= np.roll(gdil, 1, ax) | np.roll(gdil, -1, ax)
    out = dict(n_ghost=n_ghost, n_stored=int(fin.sum()),
               n_iface=int(iface.sum()))
    if iface.any():
        v = gd[iface]
        out['med_all'] = float(np.median(v))
        m_g = iface & gdil2
        m_n = iface & ~gdil2
        out['n_near'] = int(m_g.sum())
        out['n_far'] = int(m_n.sum())
        out['med_near'] = float(np.median(gd[m_g])) if m_g.any() else float('nan')
        out['med_far'] = float(np.median(gd[m_n])) if m_n.any() else float('nan')
    return out


def main():
    print('=' * 108)
    print('_r336 —— 幽灵负区 vs 界面法向模长 |∇(φ_k−φ_l)|')
    print('=' * 108)
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda p: int(re.search(r'_(\d+)\.npz$', p).group(1)))
    dx = DX
    mf = os.path.join(d, 'meta.json')
    if os.path.exists(mf):
        dx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
    print('  arm=%s  Δx=%.3f nm  快照 %d 张' % (arm, dx * 1e9, len(fs)))
    print()
    print('  %-6s %9s %10s %9s %8s %8s %10s %10s' %
          ('step', 'n_ghost', 'ghost%', 'n_iface', 'n_near', 'n_far',
           'med|∇d|近', 'med|∇d|远'))
    rows = []
    for f in fs:
        z = np.load(f, allow_pickle=True)
        if 'band_idx' not in z:
            continue
        r = analyze(z, dx)
        gp = 100.0 * r['n_ghost'] / max(r['n_stored'], 1)
        print('  %-6s %9d %9.3f%% %9d %8s %8s %10s %10s' %
              (z['step'], r['n_ghost'], gp, r['n_iface'],
               r.get('n_near', ''), r.get('n_far', ''),
               ('%.4f' % r['med_near']) if r.get('n_near') else '—',
               ('%.4f' % r['med_far']) if r.get('n_far') else '—'))
        rows.append((int(z['step']), r))
    print()
    print('  ## 判据')
    if rows:
        s0, r0 = rows[0]
        g1 = r0.get('med_all', float('nan'))
        print('  G-1 step=%d 的界面 |∇d| 中位 = **%.4f**（期望 ≈1.0）%s'
              % (s0, g1, '✅' if abs(g1 - 1.0) < 0.15 else '❌ 代理口径可疑'))
        sl, rl = rows[-1]
        print('  G-2 step %d → %d：幽灵胞 %d → %d（%.1f×）；|∇d| 中位 %.4f → %.4f'
              % (s0, sl, r0['n_ghost'], rl['n_ghost'],
                 rl['n_ghost'] / max(r0['n_ghost'], 1),
                 r0.get('med_all', float('nan')), rl.get('med_all', float('nan'))))
        if rl.get('n_near') and rl.get('n_far'):
            a, b = rl['med_near'], rl['med_far']
            print('  **G-3（决定性）** 末快照内：幽灵邻域组 %d 胞 |∇d| 中位 **%.4f**，'
                  '远离组 %d 胞 **%.4f**，相对差 **%+.2f%%**'
                  % (rl['n_near'], a, rl['n_far'], b, 100.0 * (a - b) / b))
            if a < b * 0.98:
                print('      ⇒ ✅ 幽灵邻域的 |∇d| **显著更低** ⇒ 因果链成立')
            elif a > b * 1.02:
                print('      ⇒ ❌ **反了**（幽灵邻域反而更高）⇒ 假设作废')
            else:
                print('      ⇒ ❌ **无差别**（|Δ| < 2%）⇒ 幽灵**不是**原因，假设作废')
        else:
            print('  G-3：样本不足（n_near=%s, n_far=%s）⇒ 不适用'
                  % (rl.get('n_near'), rl.get('n_far')))
    print()
    print('  ⚠ 记账：`l` 取"存下来的第二小场"，与代码的 `larr`（全局第二小）可能不同；')
    print('     `n_ghost` 是**下界**（带外 `φ_k<−6Δx` 的看不见）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
