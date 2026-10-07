#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_wtratio.py --- ★ 一个**新的**独立检验：速率的 `ΔW:ΔT` 应等于设计比 3.33

为什么这个检验比"看 ΔW:ΔL"更有信息量
--------------------------------------
设计给出迁移率比 `1 : 0.100 : 0.030`（`M ∝ exp[−β_h(n·n*)² − β_w(n·w)²]`，
`β_w=2.3`、`β_h=3.5`）。那么**任意两个方向之间的比值**都是设计预言：
  * `ΔW:ΔL = 0.100`、`ΔT:ΔL = 0.030`、**`ΔW:ΔT = 0.100/0.030 = 3.333`**。
已知本模型存在**整体各向异性被压缩**的问题（A-1：法向角噪声单边抬高 `M` 的谷底，
把差别一起压小）。而**压缩是乘性的** ⇒ 它会**同时**缩小 `ΔW:ΔL` 与 `ΔT:ΔL`，
但**`ΔW:ΔT` 这个比值对乘性压缩不敏感**（分子分母同缩）。
⇒ 所以 `ΔW:ΔT` 检验的是**另一件事**：w 与 n* 之间的**相对**各向异性对不对。

判据
----
  R-a 逐臂报有效窗口下的 `速率(ΔW)/速率(ΔT)` 与设计 **3.333** 的比；
  R-b 同时报 `ΔW:ΔL`、`ΔT:ΔL`（供对照，它们受压缩影响）；
  R-c 报不确定度（由两条回归的 σ 传播）。
"""
import csv
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
BETA_W, BETA_H = 2.3, 3.5
DESIGN_WT = float(np.exp(-BETA_W) / np.exp(-BETA_H))     # = 3.3322...


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


def load(d):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    ev = 4.0
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            ev = float(np.median(np.diff(mk)))
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    nseed = 1
    if os.path.exists(mp):
        try:
            nseed = json.load(open(mp)).get('nseed') or 1
        except Exception:                                            # noqa: BLE001
            pass
    st = np.arange(len(rows), dtype=float) * ev
    L = np.array([fnum(r, 'L_cal') for r in rows])
    W = np.array([fnum(r, 'W_cal') for r in rows])
    T = np.array([fnum(r, 'T_cal') for r in rows])
    g1 = np.array([fnum(r, 'box_touch') for r in rows]) <= 0
    g2 = np.array([fnum(r, 'ncomp') for r in rows]) <= 1
    good = g1 & g2 & np.isfinite(L) & np.isfinite(W) & np.isfinite(T)
    return st, L, W, T, good, nseed


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0]))


print('=' * 100)
print('速率的 `ΔW:ΔT` —— 设计比 = exp(−%.1f)/exp(−%.1f) = **%.4f**（对乘性各向异性压缩不敏感）'
      % (BETA_W, BETA_H, DESIGN_WT))
print('=' * 100)
print('%-16s %6s %10s %10s %10s %10s %12s'
      % ('臂', 'nseed', 'ΔW:ΔL', 'ΔT:ΔL', 'ΔW:ΔT', 'vs 设计', '窗口'))
ARMS = sys.argv[1:] or ['lath192_ns4', 'mid192_ns4', 'mid192_s2_ns4',
                        'mid250_ns4', 'mid250_base', 'mid1', 'lath1']
for d in ARMS:
    o = load(d)
    if o is None:
        continue
    st, L, W, T, good, nseed = o
    if nseed > 1:
        print('%-16s  （多核臂，本检验不适用）' % d); continue
    base = st[8] if len(st) > 8 else st[0]
    last = st[good].max() if good.any() else st[-1]
    m = good & (st >= base) & (st <= last)
    if int(m.sum()) < 8:
        print('%-16s  ✗ 有效采样不足' % d); continue
    t = st[m]
    sL, eL = fit(t, L[m])
    sW, eW = fit(t, W[m])
    sT, eT = fit(t, T[m])
    if sL <= 0 or sW <= 0 or sT <= 0:
        print('%-16s  ✗ 有非正速率' % d); continue
    rWL, rTL = sW / sL, sT / sL
    rWT = sW / sT
    eWT = rWT * np.sqrt((eW / sW) ** 2 + (eT / sT) ** 2)
    print('%-16s %6d %10.4f %10.4f %10.3f±%.3f %10.2f× %12s'
          % (d, nseed, rWL, rTL, rWT, eWT, rWT / DESIGN_WT,
             '[%g,%g]' % (base, last)))
print('=' * 100)
print('判读：`ΔW:ΔT` **接近 3.33** ⇒ w 与 n* 之间的**相对**各向异性是对的；')
print('      而 `ΔW:ΔL`/`ΔT:ΔL` 同时偏大 ⇒ 是**整体乘性压缩**（A-1）所致，两者不矛盾。')
print('      ⚠ 仍是 2 个 Δx 点、且各臂窗口不同 ⇒ 报数时必须带窗口（见台账 B-1b/B-1d）。')
print('=' * 100)
