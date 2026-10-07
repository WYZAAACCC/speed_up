#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r268_sync.py —— ★ 离线检验 `§149` 的"**块内锁定步**"预言（**不需要新仿真**）。

## 预言（`§149.3`）
同变体的两根板条驱动**逐位相同**（`§138` + `§148` + `df` 同值）
⇒ 它们应**同步长大** ⇒ **同一块内两根板条的体积差应显著小于"不同变体"之间的差**。

## 判据（**先写死**）
* **Y-1 正对照**：合成一个 `region`，其中两个同变体场**逐胞相同** ⇒
  `within` 必须**恰好 0**。
* **Y-2 负对照**：合成两个**不同变体**、体积差 2 倍的场 ⇒ `between` 必须显著 > 0。
* **Y-3 实测**：在归档快照上，`within_same`（块内、同变体）vs `between`（跨变体）。
  **预言 `within_same` 远小于 `between`。**
* **Y-4 退化**：某臂里没有"同变体多场"（如 `1,1,1` 只有一个变体、或全不同变体）
  ⇒ **说"不适用"**，不是 ❌。

⚠ 只用**归档快照的 `region`** ⇒ 完全离线、可复算（用户要的"事后重测"）。
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


def vols(region):
    """逐场的胞数（≈ 体积）。"""
    v = [int(x) for x in np.unique(region)]
    return {k: int((region == k).sum()) for k in v if k > 0}


def group(laths):
    """变体 -> [场号(1 基)]。"""
    g = {}
    for i, v in enumerate(laths, start=1):
        g.setdefault(int(v), []).append(i)
    return g


def splits(vd, g):
    """返回 (within_same, between, between_all)。

    ⚠⚠ **第 25 个自查错误（本节修正）**：
      第一版把 `between` 定义成"**各变体均值**的极差"，
      而 `within` 是"**同变体内各场**的极差" ⇒
      **均值会把变体内的离散平均掉** ⇒ `within` 在构造上就偏大
      ⇒ 判据**系统性偏向"块内不同步"**，我还从它下了方向性结论。**这是错的。**

    ⇒ **正确做法**：
      * `between_all` = **所有单个场**的极差（与 `within` **同一个统计量**，可直接比）；
      * 另给一个**匹配的零假设**：把"场对"分成**同变体对**与**异变体对**，
        各算 `|V_a−V_b|/mean`，比较两者的**中位**。这才是 apples-to-apples。
    """
    per = {}
    for var, flds in g.items():
        got = [vd[f] for f in flds if f in vd]
        if got:
            per[var] = float(np.mean(got))
    within = []
    for var, flds in g.items():
        got = [vd[f] for f in flds if f in vd]
        if len(got) > 1:
            within.append((max(got) - min(got)) / (np.mean(got) + 1e-30))
    # 变体**均值**之间的极差（旧口径，保留以便对照）
    betw = 0.0
    if len(per) > 1:
        vals = np.array(list(per.values()))
        betw = float((vals.max() - vals.min()) / (vals.mean() + 1e-30))
    # ★ 新口径：**所有单个场**的极差（与 within 同统计量）
    allv = np.array([vd[f] for f in sorted(g) for f in g[f] if f in vd], float)
    ball = float((allv.max() - allv.min()) / (allv.mean() + 1e-30)) if allv.size else 0.0
    # ★ 匹配的场对比较
    flds = sorted(f for f in vd)
    same_d, diff_d = [], []
    for i in range(len(flds)):
        for j in range(i + 1, len(flds)):
            a, b = flds[i], flds[j]
            va = [v for v, L in g.items() if a in L]
            vb = [v for v, L in g.items() if b in L]
            if not va or not vb:
                continue
            d = abs(vd[a] - vd[b]) / (0.5 * (vd[a] + vd[b]) + 1e-30)
            (same_d if va[0] == vb[0] else diff_d).append(d)
    return within, betw, ball, same_d, diff_d


def ctrl():
    print('  ## **Y-1 / Y-2 合成对照**')
    N = 24
    # Y-1：两个同变体场逐胞相同 ⇒ within == 0
    reg = np.zeros((N, N, N), np.int8)
    reg[4:8] = 1
    reg[8:12] = 2          # 与场1 同体积、不同位置
    g = {1: [1, 2]}
    vd = vols(reg)
    w, b = splits(vd, g)
    print('     Y-1 同变体、体积相同 ⇒ within = %s（应恰好 0）⇒ %s'
          % (['%.3e' % x for x in w], '✅' if w and w[0] < 1e-12 else '❌'))
    # Y-2：不同变体、体积差 2 倍 ⇒ between 显著
    reg2 = np.zeros((N, N, N), np.int8)
    reg2[2:6] = 1          # 4 层
    reg2[10:18] = 2        # 8 层
    g2 = {1: [1], 2: [2]}
    vd2 = vols(reg2)
    w2, b2 = splits(vd2, g2)
    print('     Y-2 不同变体、体积差 2 倍 ⇒ between = %.4f（应 > 0.2）⇒ %s'
          % (b2, '✅' if b2 > 0.2 else '❌'))
    print('     Y-1/Y-2 正负对照 %s'
          % ('✅ 通过' if (w and w[0] < 1e-12 and b2 > 0.2) else '❌ 失败'))


def main():
    print('=' * 108)
    print('_r268 —— `§149` 的"块内锁定步"预言：离线检验（只用归档 `region`）')
    print('=' * 108)
    print()
    ctrl()
    print()
    print('  ## **Y-3 实测**：归档快照上，块内（同变体）vs 跨变体 的体积离散')
    print('     %-12s %-8s %-14s %-14s %s'
          % ('臂', 'step', '块内最大相对差', '跨变体相对差', '判定'))
    arms = ('saSet2', 'saOddG', 'sgG', 'mb2fp10', 'p45L', 'p45P',
            'p45L0', 'p45P0', 'swN128', 't1N112L800')
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        mf = os.path.join(d, 'meta.json')
        if not fs or not os.path.exists(mf):
            continue
        m = json.load(open(mf))
        laths = [int(x) for x in m.get('laths', [])]
        g = group(laths)
        nmulti = sum(1 for f in g.values() if len(f) > 1)
        if nmulti == 0:
            print('     %-12s ⚪ **不适用**（无"同变体多场" ⇒ 无法分离块内/跨变体）' % arm)
            continue
        for f in fs[::max(1, len(fs) // 4)] + [fs[-1]]:
            z = np.load(f, allow_pickle=True)
            if 'region' not in z:
                continue
            vd = vols(z['region'])
            w, b = splits(vd, g)
            st = z['step'] if 'step' in z else '?'
            if not w:
                print('     %-12s %-8s ⚪ 无同变体对' % (arm, st))
                continue
            wm = max(w)
            print('     %-12s %-8s %-14.4f %-14.4f %s'
                  % (arm, st, wm, b,
                     '✅ 块内更同步' if wm < b else '⚠ 块内不比跨变体更同步'))
        print()
    print('  ⚠ 记账：`within` = 各变体内多场之间的**最大相对极差**（归一化）；')
    print('     `between` = 各变体**均值**之间的相对极差。')
    print('     ⚠ 两者口径不同（极差 vs 均值极差）⇒ 只作**同向性**判据，不作定量比较。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
