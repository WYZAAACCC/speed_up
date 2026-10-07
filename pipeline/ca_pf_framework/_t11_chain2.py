#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_chain2.py <tag>@<step> —— **用快照里的**真实轴向量**算 `Mfac`，与实测速度比对齐。

## 为什么必须重做（`R659` 记账）
`_t11_chain.py` 里我拿"设计极比 585.4"当参照 —— **那是 `Mfac(a)/Mfac(n*)`**，
而 CSV 的 `v_side_nabs` **量的是 `w` 面**（不是 `n*` 面）⇒ **分母口径不匹配**。
本工具：**直接读快照的 `n_hab`/`a_ax`/`w_ax`**，算三个面对应的 `Mfac`，
再与实测的 `v_tip`/`v_side`/`v_wide` 逐对比较 ⇒ **给出正确的兑现率**。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
BETA_H, BETA_W = 6.477, 2.3


def mfac(nd, nh, w):
    c2b = float(nd @ nh) ** 2
    c2w = float(nd @ w) ** 2
    return float(np.exp(-BETA_H * c2b - BETA_W * c2w))


for spec in (sys.argv[1:] or ["L0@300", "B40@300"]):
    tag, _, st = spec.partition('@')
    st = int(st)
    d = os.path.join(ROOT, "dry_%s" % tag)
    p = os.path.join(d, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        print("缺 %s" % p)
        continue
    with np.load(p, allow_pickle=False) as z:
        nh = np.asarray(z['n_hab'], float)
        a = np.asarray(z['a_ax'], float)
        w = np.asarray(z['w_ax'], float)
    M = {nm: mfac(nd, nh, w) for nm, nd in
         (('n*', nh), ('a', a), ('w', w), ('-n*', -nh), ('-a', -a), ('-w', -w))}
    print("=" * 100)
    print("【%s@%d】用**真实轴向量**算的 `Mfac`（β_h=%.3f, β_w=%.1f）" % (tag, st, BETA_H, BETA_W))
    print("=" * 100)
    print("  n* = [%+.5f, %+.5f, %+.5f]" % tuple(nh))
    print("  a  = [%+.5f, %+.5f, %+.5f]" % tuple(a))
    print("  w  = [%+.5f, %+.5f, %+.5f]" % tuple(w))
    print("  检核：|n*·a|=%.6f  |n*·w|=%.2e  |a·w|=%.2e"
          % (abs(nh @ a), abs(nh @ w), abs(a @ w)))
    print()
    for nm in ('n*', 'a', 'w'):
        print("  Mfac(%s)  = **%.6g**" % (nm, M[nm]))
    print()
    print("  ⇒ **设计速度比（本口径）**：")
    for nm, num, den in (('v_tip / v_side', 'a', 'w'),
                         ('v_tip / v_wide', 'a', 'n*'),
                         ('v_wide / v_side', 'n*', 'w')):
        print("     %-16s = Mfac(%s)/Mfac(%s) = **%.3f**"
              % (nm, num, den, M[num] / M[den]))
    # 实测
    cp = os.path.join(d, "series.csv")
    if os.path.exists(cp):
        got = None
        with open(cp, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                try:
                    if int(r["step"]) == st:
                        got = r
                        break
                except (KeyError, ValueError):
                    pass
        if got:
            def g(k):
                try:
                    return float(got.get(k, "") or "nan")
                except ValueError:
                    return float("nan")
            vt, vs, vw = g("v_tip_nabs"), g("v_side_nabs"), g("v_wide_nabs")
            print()
            print("  ⇒ **实测速度（CSV，同 step）**：v_tip=%.4g  v_side=%.4g  v_wide=%.4g" %
                  (vt, vs, vw))
            print("     推导（`_bk_measure.py` 的面分类：tip=`a` / side=`w` / wide=`n*`）")
            for nm, meas, des in (('v_tip/v_side = Mfac(a)/Mfac(w)', vt / vs, M['a'] / M['w']),
                                  ('v_tip/v_wide = Mfac(a)/Mfac(n*)', vt / vw, M['a'] / M['n*']),
                                  ('v_wide/v_side = Mfac(n*)/Mfac(w)', vw / vs, M['n*'] / M['w'])):
                print("     %-34s 实测 **%8.3f**  设计 %8.3f  ⇒ 兑现率 **%6.1f%%**"
                      % (nm, meas, des, 100 * (meas - 1) / (des - 1) if abs(des - 1) > 1e-9 else float('nan')))
