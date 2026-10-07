#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r117_betafilm.py —— **裂块是"真分开"还是"1 胞厚 β 膜"？**（判据：`snapshot_coverage`）

## 为什么（本轮的第二个新观测）

`_r116` 实测：`saPair`/`saOdd`（弹性开）在 step 20 就把"2 根一块"裂成 8–11 块；
而 **`saPairE0`（`--el-scale 0`，**同样**开了 `--facet-proj 10`）保持 6/6 不裂**
⇒ **裂块与保面机制无关**（保面被这条**内建对照**洗清），与**弹性驱动**相关。

## 但"裂成两块"有两种完全不同的机制，必须分开

| 机制 | 特征 | 是不是缺陷 |
|---|---|---|
| **A. 真的分开了**（中间长出母相） | β 夹层**厚**（≥2 胞） | **是物理**（可能是真的） |
| **B. 1 胞厚 β 膜**（阶梯错位伪影） | β 夹层**恰好 1 胞**、`cov` 掉下来 | **是数值伪影**（`dry_gs2` 的老毛病，`_bk_exp.py:708-721` 有完整机理） |

**判据（`_bk_measure.snapshot_coverage`，已有 C16/C17 正负对照）**：
* `cov` = `Σ F3 面积 / [Σ单根宽面面积·(M−1)/M]`；本倾角/分辨率下**天花板 0.85–0.96**；
* `beta_frac[(i,j)]` = 第 (i,j) 对的 β 占比；**底噪 ~0.15**、判据 **≤ 0.25**；
* `beta_cells[(i,j)]` = 夹层 β **体素数** ⇒ 除以界面面积可以估**膜厚**（胞数）。

⇒ **膜厚 ≈ 1 胞 且 `beta_frac` 高** ⇒ 机制 B（伪影）；**膜厚 ≥ 2–3 胞** ⇒ 机制 A（真分开）。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bk_measure as BM                                    # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = ['saPair', 'saPairE0', 'saOdd']


def step_of(p):
    return int(re.search(r'snap_(\d+)\.npz$', p).group(1))


def main():
    print('=' * 110)
    print('_r117 —— 裂块机制：真分开（膜厚 ≥2 胞） vs 1 胞 β 膜（伪影）')
    print('=' * 110)
    for t in ARMS:
        fs = sorted(glob.glob(os.path.join(MB, 'dry_' + t, 'snap_*.npz')),
                    key=step_of)
        if not fs:
            print('  %-10s （无快照）' % t)
            continue
        print()
        print('  ### %-10s（%d 个快照）' % (t, len(fs)))
        print('     %-6s %-8s %-9s %-9s %-10s %s'
              % ('step', 'cov', 'f3_area', 'exp_int', '最差对', '各对 β 占比 / 膜厚(胞)'))
        for p in fs[:6]:
            z = np.load(p)
            if 'region' not in z.files:
                print('     ⚠ 快照无 region'); break
            try:
                c = BM.snapshot_coverage(z)
            except Exception as e:
                print('     step %-4d ⚠ %s' % (step_of(p), str(e)[:60]))
                continue
            bf = c.get('beta_frac', {}) or {}
            bc = c.get('beta_cells', {}) or {}
            src = z['region']
            dx = float(z['L']) / src.shape[0]
            items = []
            for ij in sorted(bf):
                cells = bc.get(ij, 0)
                # 膜厚 ≈ 体素数 / 面积(µm²) / Δx ⇒ 胞数；面积用 F3 面积按对数均分估
                a3 = c.get('f3_area', 0.0) / max(len(bf), 1)
                th = (cells * dx ** 3) / max(a3, 1e-30) / dx if a3 > 0 else float('nan')
                items.append('%d|%d:%.2f/%.1f' % (ij[0], ij[1], bf[ij], th))
            print('     %-6d %-8.3f %-9.4f %-9.4f %-10s %s'
                  % (step_of(p), c.get('cov', float('nan')),
                     c.get('f3_area', 0.0) * 1e12, c.get('exp_int', 0.0) * 1e12,
                     str(c.get('worst')), '  '.join(items[:8])))
    print()
    print('  ---- 判读 ----')
    print('  * `cov` 掉到 ≤0.85 且各对 β 占比升到 >0.25、膜厚 ≈ **1 胞** ⇒ **机制 B（伪影）**')
    print('  * 膜厚稳定在 **≥2–3 胞** ⇒ **机制 A（真的分开）**')
    print('  ⚠ 对照基线（`snapshot_coverage` 的 docstring）：同盒同 Δx 的**预装**臂')
    print('     `dry_pa` 实测 `cov` = 0.955(t=0) / 0.884(50 步) / 0.851(100 步)，')
    print('     β 底噪 ~0.15 ⇒ **天花板 0.85–0.96、底噪 0.15** 要一起看。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
