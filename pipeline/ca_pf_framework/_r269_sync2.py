#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r269_sync2.py —— `§149` 预言的**修正版检验**（apples-to-apples 口径）。

## 为什么重写（**第 25 个自查错误**）

`_r268` 第一版：`within` = "同变体内**各场**的极差"，`between` = "各变体**均值**的极差"。
**⇒ 均值会把变体内离散平均掉 ⇒ `within` 在构造上偏大 ⇒ 判据系统性偏向"块内不同步"。**
我却从它下了方向性结论。

## 修正后的判据（**先写死**）

* **Z-1 正对照**：两个同变体场**体积相同** ⇒ `same_pairs` 中位 = **0**。
* **Z-2 负对照**：两个不同变体场体积差 2 倍 ⇒ `diff_pairs` 中位 **> 0.2**。
* **Z-3 ★ 实测**：`median(|ΔV|/V̄)` 在**同变体场对** vs **异变体场对**上谁更小。
  * `§149(A)` 的**强预言**：同变体对**显著更小**（"锁定步"）；
  * 若两者**相当** ⇒ **强预言不成立**，只能支持弱版本
    （"同变体不因变体身份而分化，差异纯由位置造成"）。
* **Z-4** 也要看**趋势**：差异是随演化**增大**还是保持。
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def vols(region):
    v = [int(x) for x in np.unique(region)]
    return {k: float((region == k).sum()) for k in v if k > 0}


def pairs(vd, g):
    flds = sorted(vd)
    same, diff = [], []
    for i in range(len(flds)):
        for j in range(i + 1, len(flds)):
            a, b = flds[i], flds[j]
            va = [v for v, L in g.items() if a in L]
            vb = [v for v, L in g.items() if b in L]
            if not va or not vb:
                continue
            d = abs(vd[a] - vd[b]) / (0.5 * (vd[a] + vd[b]) + 1e-30)
            (same if va[0] == vb[0] else diff).append(d)
    return same, diff


def ctrl():
    print('  ## **Z-1 / Z-2 合成对照**')
    N = 24
    reg = np.zeros((N, N, N), np.int8)
    reg[4:8] = 1
    reg[8:12] = 2
    s, d = pairs(vols(reg), {1: [1, 2]})
    z1 = (len(s) == 1 and s[0] < 1e-12)
    print('     Z-1 同变体、体积相同 ⇒ same_pairs = %s ⇒ %s'
          % (['%.3e' % x for x in s], '✅' if z1 else '❌'))
    reg2 = np.zeros((N, N, N), np.int8)
    reg2[2:6] = 1
    reg2[10:18] = 2
    s2, d2 = pairs(vols(reg2), {1: [1], 2: [2]})
    z2 = (len(d2) == 1 and d2[0] > 0.2)
    print('     Z-2 异变体、体积差 2 倍 ⇒ diff_pairs = %s ⇒ %s'
          % (['%.4f' % x for x in d2], '✅' if z2 else '❌'))
    print('     ⇒ 对照 %s' % ('✅ 通过' if (z1 and z2) else '❌ 失败'))
    return z1 and z2


def main():
    print('=' * 108)
    print('_r269 —— `§149` 的**修正版**检验（同变体场对 vs 异变体场对，**同口径**）')
    print('=' * 108)
    print()
    ok = ctrl()
    print()
    print('  ## **Z-3/Z-4 实测**（`median(|ΔV|/V̄)`，只用归档 `region`）')
    print('     %-12s %-7s %-16s %-16s %-10s %s'
          % ('臂', 'step', '同变体场对', '异变体场对', '比值', '判定'))
    arms = ('saSet2', 'saOddG', 'sgG', 'mb2fp10', 'p45L', 'p45P',
            'p45L0', 'p45P0', 'swN128', 't1N112L800', 'swINV128')
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        mf = os.path.join(d, 'meta.json')
        if not fs or not os.path.exists(mf):
            continue
        m = json.load(open(mf))
        laths = [int(x) for x in m.get('laths', [])]
        g = {}
        for i, v in enumerate(laths, start=1):
            g.setdefault(int(v), []).append(i)
        if not any(len(f) > 1 for f in g.values()):
            print('     %-12s ⚪ **不适用**（无同变体多场）' % arm)
            continue
        for f in fs[::max(1, len(fs) // 4)] + [fs[-1]]:
            z = np.load(f, allow_pickle=True)
            if 'region' not in z:
                continue
            s, dd = pairs(vols(z['region']), g)
            st = z['step'] if 'step' in z else '?'
            if not s or not dd:
                continue
            ms, md = float(np.median(s)), float(np.median(dd))
            r = ms / md if md > 0 else float('nan')
            print('     %-12s %-7s %-16.4f %-16.4f %-10.3f %s'
                  % (arm, st, ms, md, r,
                     '✅ 同变体更同步' if ms < md else '⚠ 同变体**不**更同步'))
        print()
    print('  ⚠ 记账：同/异变体场对用的是**同一个统计量** ⇒ 可直接比（修正了第一版的口径错配）。')
    print('  ⚠ `region` 只给**胞数**（≈ 体积），不给厚度/长度 ⇒ 这是"体积同步性"的代理。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
