#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r128_diag.py —— `_r126` 与 `_r127` 对 `w` 的结论矛盾，直接查。

`_r126`：`near(w, {110}) = 0.00` 对**全部 12 个**变体。
`_r127`：`w` 只有 **6/12** 残差 < 0.5°，另 6 个（V3/V4/V7/V8/V11/V12）给 `(0,1,0)` 且残差 **45.00°**。

⇒ 两者必有一错。本脚本把 `w` 的**原始分量**、与 6 个 `{110}` 方向的 `|cos|`、
以及 `_r127` 的候选表里最大的 `|cos|` 一起打出来。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

F110 = []
for p in set(itertools.permutations((1, 1, 0))):
    for s in itertools.product((+1, -1), repeat=3):
        v = np.array([p[i] * s[i] for i in range(3)], float)
        nv = v / np.linalg.norm(v)
        if not any(abs(float(nv @ w)) > 1 - 1e-9 for w in F110):
            F110.append(nv)
F110 = np.array(F110)


def npf(v):
    try:
        return np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        return np.asarray(NPF[v - 1], float)


def axes(v):
    e = np.asarray(EPS0[v - 1], float)
    R = WS.LevelSetMulti._rank1_axes(e, npf(v))
    return (npf(v) / np.linalg.norm(npf(v)),
            np.asarray(R[1], float) / np.linalg.norm(R[1]),
            np.asarray(R[2], float) / np.linalg.norm(R[2]))


def main():
    print('=' * 100)
    print('_r128 —— `w` 到底是哪个方向？（`_r126` vs `_r127`）')
    print('=' * 100)
    print('  `F110` 元素数 = %d' % len(F110))
    for i, h in enumerate(F110):
        print('     [%d] %s' % (i, np.array2string(h, precision=6)))
    print()
    print('  %-4s %-34s %-9s %-14s %s'
          % ('变体', '`w` 原始分量', 'max|w·{110}|', 'argmax 的 {110}', 'near(°)'))
    for v in range(1, 13):
        n, a, w = axes(v)
        c = np.abs(F110 @ w)
        i = int(np.argmax(c))
        ang = float(np.degrees(np.arccos(np.clip(c[i], -1, 1))))
        print('  V%-3d %-34s %-9.6f %-14s %.4f'
              % (v, np.array2string(w, precision=6), c[i],
                 np.array2string(F110[i], precision=4), ang))
    print()
    print('  ---- 同时检查 `_r127` 的候选表里 `(1,1,0)` 在不在 ----')
    MAXI = 8
    TRIP = []
    for h in range(0, MAXI + 1):
        for k in range(0, MAXI + 1):
            for l in range(0, MAXI + 1):
                if h == k == l == 0:
                    continue
                g = int(np.gcd(np.gcd(h, k), l)) or 1
                t = (h // g, k // g, l // g)
                if t not in TRIP:
                    TRIP.append(t)
    print('     候选数 = %d；`(1,1,0)` 在里面吗？ %s；`(0,1,1)`？ %s；`(1,0,1)`？ %s'
          % (len(TRIP), (1, 1, 0) in TRIP, (0, 1, 1) in TRIP, (1, 0, 1) in TRIP))
    CN = np.array(TRIP, float)
    CN = CN / np.linalg.norm(CN, axis=1, keepdims=True)
    w1 = axes(3)[2]
    c = np.abs(CN @ w1)
    i = int(np.argmax(c))
    print('     V3 的 `w`：候选表里的 argmax = %s、|cos| = %.6f（%s）'
          % (TRIP[i], c[i], '**应等于 √2/2=0.7071 才对**'
             if abs(c[i] - 0.70710678) < 1e-4 else 'ok'))
    c2 = np.abs(F110 @ w1)
    print('     V3 的 `w`：`F110` 里的 max|cos| = %.6f' % c2.max())
    return 0


if __name__ == '__main__':
    sys.exit(main())
