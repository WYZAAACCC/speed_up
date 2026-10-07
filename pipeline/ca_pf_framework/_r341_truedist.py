#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r341_truedist.py —— ★★ `|∇φ_k|` 退化：**去掉 `|φ|` 分桶的循环论证**。

## 为什么必须再做一次

`_r339` 按 `|φ_k|/Δx` 分桶，发现**大 `|φ|` 桶**（⊂ 厚特征）也从 0.99 掉到 0.60–0.73
⇒ 否掉了"中轴伪影（良性）"这个解释。

**但 `_r339` 自己有一个循环论证**：分桶用的是 `|φ_k|`，
而"φ 被拉伸"正是被检验的假设本身 —— 若 φ 拉伸 2×，则 `|φ|=5Δx` 的真实深度只有 2.5 胞。
⇒ **分桶必须用一个与 φ 无关的深度**。

## 做法

深度用**归档 `region` 图**算：先取"6-邻域里 region 不同"的胞为界面，
再做**逐次膨胀**得到每个胞到最近界面的**真实胞距** `D`（与 φ 完全无关）。
然后在 `{region==k, φ_k<0, φ_k 存下来}` 上按 `D` 分桶统计 `|∇φ_k|`。

## 判据（**先写死**）

* **U-0**：`step=0` 的**每个** `D` 桶都 ≈ 1.0。
* **U-1**（缺陷成立）：末快照上 **`D ≥ 3` 胞**的桶（**真·厚区**，与 φ 无关）
  中位仍 **< 0.9**。
* **U-2**（良性/伪影）：只有 `D ≤ 1` 的桶低，`D ≥ 3` 的桶 ≥ 0.9。
* **U-3 副产物**：若 `D ≥ 3` 的胞**很少**，说明结构已经很细 ⇒ 单独记账，不得当"厚区"用。
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
DMAX = 10


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


def true_dist(reg):
    """到最近 region 边界的**真实胞距**（逐次膨胀；与 φ 无关）。"""
    bnd = np.zeros(reg.shape, bool)
    for ax in range(3):
        bnd |= (reg != np.roll(reg, 1, ax)) | (reg != np.roll(reg, -1, ax))
    cur = bnd.copy()
    dist = np.full(reg.shape, 255, np.uint8)
    dist[cur] = 0
    for s in range(1, DMAX):
        nxt = cur.copy()
        for ax in range(3):
            nxt |= np.roll(cur, 1, ax) | np.roll(cur, -1, ax)
        new = nxt & ~cur
        dist[new] = s
        cur = nxt
    return dist


def main():
    print('=' * 112)
    print('_r341 —— |∇φ_k| 退化（用 region 的真实胞距分桶，去掉循环论证）')
    print('=' * 112)
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2'
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    dx = 62.5e-9
    mf = os.path.join(d, 'meta.json')
    if os.path.exists(mf):
        dx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
    print('  arm=%s  Δx=%.3f nm' % (arm, dx * 1e9))
    print()
    print('  %-6s' % 'step' + ''.join(' %14s' % ('D=%d' % i) for i in range(1, 8)))
    for f in (fs[0], fs[len(fs) // 2], fs[-1]):
        z = np.load(f, allow_pickle=True)
        if 'band_idx' not in z:
            continue
        reg = np.asarray(z['region'], np.int64)
        N = int(z['N'])
        p = rebuild(z)
        nf = p.shape[0]
        fin = np.isfinite(p)
        kk = np.arange(nf)[:, None, None, None]
        legal = fin & (p < 0.0) & (reg[None] == kk)
        gphi = np.stack([gmag(p[k].astype(np.float64), dx) for k in range(nf)], 0)
        D = true_dist(reg)
        cells = []
        for i in range(1, 8):
            m = legal & (D == i) & np.isfinite(gphi)
            n = int(m.sum())
            cells.append('%8.4f(%d)' % (float(np.median(gphi[m])), n)
                         if n >= 50 else '    —(%d)' % n)
        print('  %-6s' % z['step'] + ''.join(' %14s' % c for c in cells))
    print()
    print('  ## 判据')
    print('  * **U-0**：step 0 每个 D 桶 ≈ 1.0 ⇒ 口径可信。')
    print('  * **U-1**（缺陷）：末快照 **D ≥ 3** 的桶 < 0.9。')
    print('  * **U-2**（伪影）：只有 D ≤ 1 低，D ≥ 3 ≥ 0.9。')
    print('  * **U-3**：若 D ≥ 3 的胞数很少 ⇒ 结构已变细，单独记账。')
    print()
    print('  ⚠ 记账：`D` 由 `region` 的 6-邻域差分 + 膨胀得到，**与 φ 完全无关**；')
    print('     但它是**盒内**距离，周期边界处 `np.roll` 会绕过去（与引擎同一约定）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
