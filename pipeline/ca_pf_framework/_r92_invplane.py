#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r92_invplane.py —— **不变平面法向到底是哪根轴**（最小、最直接的判据）。

## 判据（教科书，一行）

不变平面（惯习面）应变 `F = I + m·d pᵀ`（`p` = 惯习面法向，`d·p = 0`）满足

    @@F^{\\mathsf T}p=p@@   ⟺   @@\\boldsymbol\\varepsilon^{\\mathsf T}p=0@@（小应变）

⇒ **哪根轴 `u` 让 `‖εᵀu‖` 最小（≈0），哪根就是惯习面法向。**
这是**一行**的判据，不依赖任何搜索、不依赖 `{334}` 极、不依赖采样。

## 为什么必须做（`_r89`/`_r90`/`_chk_habit5` 的教训链）

1. `_r89` 用 `F = I + EPS0_T16` ⇒ `|λ−1| = 4.17e-4`、12/12 精确 90.00° ⇒ 我据此
   宣布"P1-40：`NPF` 与 `EPS0` 不一致"。**那是错的**（12 个同值 90° 是"判据错"的指纹）。
2. `_r90` 换成真 `FV` ⇒ 结构清楚了：`n_inv` 的配对结构与 `EPS0` **6/6 吻合**，
   但 `NPF` 仍 90°。
3. `_r91` ⇒ **`n_inv` 精确等于 `w` 轴（0.00°，12/12）**，不是 `n*`。
4. `_chk_habit5.py`（自称"定案"）⇒ **H-9 与 H-10 都是 FAIL**，
   它把 `n_inv`（= `w`）当成 `n*` 的"解析真值"在比 ⇒ **必然 ~90° FAIL**。

⇒ 现在直接量 `‖εᵀu‖` 对三根轴，一次说清：**惯习面法向是 `n*`、`a`、还是 `w`。**
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0 as EPS0_T16, NPF             # noqa: E402
from windowB_ti64_variants import variants                   # noqa: E402

EPS0V, FV, _M = variants()
NV = len(FV)


def npf(v):
    try:
        a = np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        a = np.asarray(NPF[v - 1], float)
    return a / np.linalg.norm(a)


def main():
    print('=' * 112)
    print('_r92_invplane —— 哪根轴满足 `εᵀu = 0`（= 不变平面法向）')
    print('=' * 112)
    # 先确认两份 EPS0 是否同一个东西（**口径先行**）
    d = max(float(np.max(np.abs(np.asarray(EPS0V[i], float)
                                - np.asarray(EPS0_T16[i], float))))
            for i in range(NV))
    print('  `windowB_ti64_variants.EPS0` 与 `T16_verify_rve.EPS0` 的最大逐元差 = %.3e %s'
          % (d, '（同一个东西）' if d < 1e-12 else '⚠ **不是同一个东西**'))
    print()
    print('  %-4s %-13s %-13s %-13s %-11s %s'
          % ('变体', '‖εᵀn*‖/‖ε‖', '‖εᵀa‖/‖ε‖', '‖εᵀw‖/‖ε‖', 'argmin', 'ε 的迹'))
    cnt = {'n*': 0, 'a': 0, 'w': 0}
    for v in range(1, NV + 1):
        e = np.asarray(EPS0V[v - 1], float)
        nrm = float(np.linalg.norm(e))
        n = npf(v)
        R = WS.LevelSetMulti._rank1_axes(e, n)
        a = np.asarray(R[1], float); a /= np.linalg.norm(a)
        w = np.asarray(R[2], float); w /= np.linalg.norm(w)
        rn = float(np.linalg.norm(e.T @ n)) / nrm
        ra = float(np.linalg.norm(e.T @ a)) / nrm
        rw = float(np.linalg.norm(e.T @ w)) / nrm
        k = min((rn, 'n*'), (ra, 'a'), (rw, 'w'))[1]
        cnt[k] += 1
        print('  V%-3d %-13.4e %-13.4e %-13.4e %-11s %+.4e'
              % (v, rn, ra, rw, k, float(np.trace(e))))
    print()
    print('  ⇒ `εᵀu ≈ 0` 命中的轴：%s' % cnt)
    print()
    # ---- rank-1 判定：det(eps) 应为 0（tr=0 时 ⟺ 存在不变平面）----
    dets = [float(np.linalg.det(np.asarray(EPS0V[i], float))) for i in range(NV)]
    sc = [float(np.linalg.norm(np.asarray(EPS0V[i], float))) for i in range(NV)]
    print('  rank-1 检查：`det(ε)/‖ε‖³` 的 max = %.3e（真 rank-1 ⇒ 0）'
          % max(abs(dets[i]) / sc[i] ** 3 for i in range(NV)))
    print('     ⇒ %s'
          % ('**ε 是 rank-1（存在精确不变平面）** —— 那么 `εᵀu = 0` 的 u 就是精确法向'
             if max(abs(dets[i]) / sc[i] ** 3 for i in range(NV)) < 1e-9
             else '**ε 不是精确 rank-1** ⇒ 只有"准"不变平面（与 `windowB_nucleus` 的'
                  ' `lambda2 = 1.00042` 一致）'))
    print()
    print('  ---- 结论怎么读 ----')
    print('  * 若命中的是 `n*`（= `NPF`）⇒ 模型的惯习面法向**正确**，`_chk_habit5` 的')
    print('    FAIL 是它自己把 `w` 当成了 `n*`（**诊断脚本的 bug，不是物理的 bug**）。')
    print('  * 若命中的是 `w` ⇒ 模型把**宽度方向**当成了板条厚向 ⇒ **是物理层的缺陷**，')
    print('    需要升级为 P0 并与用户确认。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
