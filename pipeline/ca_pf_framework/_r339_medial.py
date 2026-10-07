#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r339_medial.py —— ★★ `|∇φ_k|` 掉一半：**真·拉伸** 还是 **中轴伪影**？

## 问题

`_r338` 实测（`saSet2`，21 张快照）：
* **S-1 标定 ✅**：step 0 的合法内部 `|∇φ_k|` 中位 = **0.9919**（70699 胞）
  ⇒ 引擎的 φ 在 t=0 **就是**单位距离函数，口径可信；
* **S-2 退化**：step 0 → 400，**0.9919 → 0.4798（−51.6%）**，单调，与幽灵数同步。

**但"掉一半"有两个完全不同的解释**：

* **H-A 中轴伪影（良性）**：结构随时间长细（薄片/薄壁），薄特征里**每个胞都靠近中轴**，
  而距离函数在中轴上是"脊"（`|∇φ|` 数值上 < 1）⇒ 中位被拉低。
  **物理与动力学不受影响**（界面附近仍有 `|∇φ|≈1`）。
* **H-B 真·拉伸（缺陷）**：场被普遍拉长，**厚特征的内部也**不再是距离函数
  ⇒ 界面法向 `∇(φ_k−φ_l)` 的**方向**也随之失真 ⇒ 各向异性被破坏。

## 判据（**先写死**）

按 `|φ_k|/Δx` 分桶统计 `|∇φ_k|` 中位。**薄特征的全部胞都在小 `|φ|` 桶里**，
**厚特征**才有大 `|φ|` 桶 ⇒ 两个假设给出**相反**的预测：

* **T-1**：末快照的**大 `|φ|` 桶**（`|φ| ≥ 3Δx`）中位仍 **≥ 0.9** ⇒ **H-A（良性）**。
* **T-2**：所有桶**成比例**下降（大桶也掉到 ~0.5）⇒ **H-B（缺陷）**。
* **T-0 前提**：step 0 的所有桶都必须 ≈ 1.0（否则分桶口径本身有问题）。
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
EDGES = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.01]


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


def main():
    print('=' * 112)
    print('_r339 —— |∇φ_k| 掉一半：真·拉伸 还是 中轴伪影？')
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
    hdr = '  %-6s' % 'step' + ''.join(' %14s' % ('[%.1f,%.1f)' % (EDGES[i], EDGES[i + 1]))
                                      for i in range(len(EDGES) - 1))
    print(hdr)
    picks = [fs[0], fs[len(fs) // 4], fs[len(fs) // 2], fs[-1]]
    picks = sorted(set(picks), key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    for f in picks:
        z = np.load(f, allow_pickle=True)
        if 'band_idx' not in z:
            continue
        reg = np.asarray(z['region'], np.int64)
        p = rebuild(z)
        nf = p.shape[0]
        fin = np.isfinite(p)
        kk = np.arange(nf)[:, None, None, None]
        legal = fin & (p < 0.0) & (reg[None] == kk)
        gphi = np.stack([gmag(p[k].astype(np.float64), dx) for k in range(nf)], 0)
        av = np.abs(p) / dx
        cells = []
        for i in range(len(EDGES) - 1):
            m = legal & (av >= EDGES[i]) & (av < EDGES[i + 1]) & np.isfinite(gphi)
            n = int(m.sum())
            if n < 50:
                cells.append('     —(n<%d)' % n if n else '          —')
            else:
                cells.append('%8.4f(%d)' % (float(np.median(gphi[m])), n))
        print('  %-6s' % z['step'] + ''.join(' %14s' % c for c in cells))
    print()
    print('  ## 判据')
    print('  * **T-0**：step 0 的**所有**桶都 ≈ 1.0 ⇒ 分桶口径可信。')
    print('  * **T-1**（H-A 良性）：末快照的**大 `|φ|` 桶（≥3Δx）**中位仍 ≥ 0.9。')
    print('  * **T-2**（H-B 缺陷）：所有桶**成比例**下降。')
    print()
    print('  ⚠ 记账：桶内胞数随结构演化而变（薄特征变多 ⇒ 小桶变大桶变小），')
    print('     所以**不能**只看"总体中位"的走势 —— 必须**分桶**看。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
