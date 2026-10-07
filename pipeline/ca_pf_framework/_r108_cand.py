#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r108_cand.py —— **挑一个"不可自协调 + 几何可放"的变体集**（纯离线，秒级）。

## 问题

自协调实验需要一个**不可自协调**的对照臂（`saPair`）。`{1..6}` 满足"不可自协调"
（`r_min = 0.4828`）但几何上**放不下**：它的布局轴 `u = Σ a_b` 归一化后是 **`[0,1,0]`**
（一条直线沿 y）⇒ 6 个块沿 y 排开，间距小则重叠、间距大则顶出盒壁（`_r104/_r107` 实测）。

## 本脚本

枚举 **所有 6 变体子集**（`C(12,6) = 924` 个），对每个算：
  1. `r_min(G)`（单纯形最小残差）—— **越大越好**（越"不可自协调"）；
  2. **布局轴** `u = normalize(Σ_{v∈G} a_v)`（与 `_bk_exp.py` 的多块播种**同一算法**）；
  3. **直线度** `straight = |Σ a_v| / 6`（=1 ⇒ 完全同向 ⇒ 一条直线 ⇒ 难放；
     小 ⇒ 各向散开 ⇒ 好放）；
  4. 块的 `a` 轴在布局轴方向的投影和 `Σ|a_v·u|`（越大 ⇒ 块沿布局轴越长 ⇒ 越易重叠）。

⇒ 挑"`r_min` 大 **且** `straight` 小"的集合做对照臂。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
import windowB_surface as WS                                # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

E_ALL = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0]
SCALE = float(np.mean([np.linalg.norm(e) for e in E_ALL]))
VEC = np.array([e.reshape(-1) for e in E_ALL])


def npf(v):
    try:
        a = np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        a = np.asarray(NPF[v - 1], float)
    return a / np.linalg.norm(a)


def aax(v):
    R = WS.LevelSetMulti._rank1_axes(np.asarray(EPS0[v - 1], float), npf(v))
    a = np.asarray(R[1], float)
    return a / np.linalg.norm(a)


def main():
    A = {v: aax(v) for v in range(1, 13)}
    print('=' * 104)
    print('_r108 —— 924 个六元组：`r_min` vs 布局轴直线度（挑对照臂用）')
    print('=' * 104)
    rows = []
    for G in itertools.combinations(range(1, 13), 6):
        rmin = R78._simplex_r(VEC[[v - 1 for v in G]], SCALE)
        s = np.sum([A[v] for v in G], axis=0)
        sn = float(np.linalg.norm(s))
        straight = sn / 6.0
        u = s / sn if sn > 1e-9 else np.array([0.0, 0.0, 1.0])
        proj = float(sum(abs(float(A[v] @ u)) for v in G))
        rows.append((rmin, straight, proj, G))
    # 判据：r_min 大（不可自协调）且 straight 小（好放）
    rows.sort(key=lambda t: (-(t[0] > 0.45), t[1]))
    print('  %-30s %-10s %-11s %-9s %s'
          % ('集合', 'r_min', '直线度', 'Σ|a·u|', '备注'))
    shown = 0
    for rmin, straight, proj, G in rows:
        if rmin < 0.45:
            continue
        flag = ''
        if straight < 0.35:
            flag = '★ **候选**（不可自协调 + 好放）'
        print('  %-30s %-10.4f %-11.3f %-9.2f %s'
              % (str(list(G)), rmin, straight, proj, flag))
        shown += 1
        if shown >= 16:
            break
    print()
    # 三个已知集的对照
    print('  ---- 已知集 ----')
    for lab, G in (('{1..6}（历史 P-SA-1 用的）', tuple(range(1, 7))),
                   ('{1,3,5,7,9,11}（奇，可自协调）',
                    (1, 3, 5, 7, 9, 11)),
                   ('{2,4,6,8,10,12}（偶，可自协调）',
                    (2, 4, 6, 8, 10, 12))):
        rmin = R78._simplex_r(VEC[[v - 1 for v in G]], SCALE)
        s = np.sum([A[v] for v in G], axis=0)
        sn = float(np.linalg.norm(s))
        u = s / sn if sn > 1e-9 else np.array([0.0, 0.0, 1.0])
        proj = float(sum(abs(float(A[v] @ u)) for v in G))
        print('  %-34s r_min=%-9.4f 直线度=%-8.3f Σ|a·u|=%.2f  u=%s'
              % (lab, rmin, sn / 6.0, proj, np.array2string(u, precision=3)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
