#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r127_miller.py —— **把 `NPF`/`a`/`w` 化成有理 Miller 指数**（不预设族，让数据说话）。

## 为什么（`§93` 的收尾路线）

`_r126` 定出：**`w` 精确等于 `{110}β`（12/12，0.00°）** ⇒ **β 笛卡尔系 = 立方晶轴系**成立
（`_chk_habit5.py:23-24` 也是这么写的）。
但 `n*`/`a` 到 `{433}` 分别是 2.68–7.99°（**不是**精确匹配），到 `{110}`/`{111}` 更远。

⇒ **不要再猜族**：直接把 `n*`、`a`、`w` 各自**化成最简有理指数**。
若某个轴是 `(hkl)` 型晶向/晶面法向，它必然能写成**小整数**比，且残差角 ≈ 0。

## 判据

对单位向量 `u`，在 `|h|,|k|,|l| ≤ 8` 的全部整数方向里取夹角最小者；
报 **最简指数** 与 **残差角**。**残差 < 0.5° ⇒ 该轴是有理方向**。

**正对照**：取 `H334` 的一个元素微扰 0.1° ⇒ 必须恢复成 `(4,3,3)` 且残差 ≈ 0.1°。
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

MAXI = 8
# ★★★ 修（**本脚本第一版的错**）：候选**不能**只取非负三元组！
#   `(1,1,0)` 与 `(-1,1,0)` 是**两条不同的线**（互相正交），不是同一线的符号变体
#   ⇒ 实测 V3 的 `w = (-0.7071, +0.7071, 0)` 与 `(1,1,0)` 的 `|cos| = 0`
#   ⇒ 第一版把它误判成 `(0,1,0)`、残差 45°。
#   ⇒ 正确做法：**每个位置的符号独立**（与 `_r126` 的 `family()` 一致），
#     再用 `|u·w| > 1-1e-9` 按**线**去重。
_TRIP = []
_NORM = []
for h in range(-MAXI, MAXI + 1):
    for k in range(-MAXI, MAXI + 1):
        for l in range(-MAXI, MAXI + 1):
            if h == k == l == 0:
                continue
            g = int(np.gcd(np.gcd(abs(h), abs(k)), abs(l))) or 1
            t = (h // g, k // g, l // g)
            v = np.array(t, float)
            nv = v / np.linalg.norm(v)
            if any(abs(float(nv @ w)) > 1 - 1e-9 for w in _NORM):
                continue
            _NORM.append(nv)
            _TRIP.append(t)
CAND_N = np.array(_NORM)
print('# 候选**线**数 = %d（`|h|,|k|,|l| <= %d`，最简，按线去重）' % (len(_TRIP), MAXI))


def miller(u):
    """返回 `((h,k,l), 残差角°)`。"""
    u = np.asarray(u, float)
    u = u / np.linalg.norm(u)
    c = np.abs(CAND_N @ u)
    i = int(np.argmax(c))
    ang = float(np.degrees(np.arccos(np.clip(c[i], -1, 1))))
    return _TRIP[i], ang


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
    print('=' * 108)
    print('_r127 —— `NPF`/`a`/`w` 的最简有理指数（不预设族）')
    print('=' * 108)
    # ---- 正对照 ----
    base = np.array([4.0, 3.0, 3.0]); base /= np.linalg.norm(base)
    ax = np.array([1.0, -1.0, 0.0]); ax /= np.linalg.norm(ax)
    pert = base * np.cos(np.radians(0.1)) + ax * np.sin(np.radians(0.1))
    m, a = miller(pert)
    print('  **正对照**：把 `(4,3,3)` 微扰 0.10° ⇒ 恢复 %s、残差 %.4f°（应 ≈0.1）'
          % (m, a))
    print('     ⇒ 判据 %s' % ('PASS' if (m == (3, 3, 4) or m == (4, 3, 3))
                              and a < 0.5 else '**FAIL ⇒ 下面作废**'))
    print()
    print('  %-4s %-20s %-20s %s' % ('变体', '`n*` → 指数(残差°)',
                                     '`a` → 指数(残差°)', '`w` → 指数(残差°)'))
    cnt = {'n*': [], 'a': [], 'w': []}
    for v in range(1, 13):
        n, a_, w = axes(v)
        mn, dn = miller(n)
        ma, da = miller(a_)
        mw, dw = miller(w)
        cnt['n*'].append((mn, dn)); cnt['a'].append((ma, da)); cnt['w'].append((mw, dw))
        print('  V%-3d %-20s %-20s %s'
              % (v, '%s (%.2f)' % (mn, dn), '%s (%.2f)' % (ma, da),
                 '%s (%.2f)' % (mw, dw)))
    print()
    for key in ('n*', 'a', 'w'):
        arr = cnt[key]
        exact = [t for t, d in arr if d < 0.5]
        from collections import Counter
        print('  `%s`：残差 < 0.5° 的 **%d/12**；指数分布 %s'
              % (key, len(exact), dict(Counter(t for t, _ in arr))))
    print()
    print('  ---- 裁决 ----')
    for key in ('n*', 'a', 'w'):
        ex = sum(1 for _, d in cnt[key] if d < 0.5)
        print('     `%s` 是有理方向的个数：%d/12' % (key, ex))
    return 0


if __name__ == '__main__':
    sys.exit(main())
