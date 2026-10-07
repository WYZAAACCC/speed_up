#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_wtratio2.py --- B-18 的下一步：把 `ΔW:ΔT` 做成**窗口分辨**，并在**共同窗口**上比 m=0 vs m=4。

为什么必须做窗口分辨（台账 B-1b / B-18）
----------------------------------------
`_r1_wtratio.py` 报的是"每臂一个数"，而速率的**窗口不同**、且**非平稳**
（实测 `mid250_ns4` 的 `ΔW:ΔL` 漂 56%）。
所以 m=0（0.88–0.96×）与 m=4（0.90–1.70×）的差别**可能只是窗口效应**。
本脚本对每个臂给出 `ΔW:ΔT(hi)` 曲线，并**只在与其它臂共同的 `hi` 上**比较。

判据
----
  S-1 逐臂逐窗口的 `ΔW:ΔT`（窗口左端固定 = 第 8 个采样，右端 `hi`）；
  S-2 **共同窗口**上 m=0 组 vs m=4 组的对比（同 `hi` 相比才合法）；
  S-3 报每组的散布：若两组的 `ΔW:ΔT(hi)` 区间**重叠** ⇒
      B-18 的"m=0 更接近设计"**不成立**（是窗口效应）；不重叠 ⇒ 该差异**真实存在**。
"""
import csv
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
DESIGN = float(np.exp(-2.3) / np.exp(-3.5))          # 3.3201
I0 = 8
# ★ 允许用命令行指定要比较的两组（默认是 m-扫描的两组）。
#   为什么需要：`ΔW:ΔT` 必须**在共同窗口上**比才有意义
#   （速率比非平稳，B-1b）。例如验收靶重做后要比 `mid192_ns4` vs `mid192_ns4b`。
if len(sys.argv) > 2:
    _half = (len(sys.argv) - 1) // 2
    M0 = sys.argv[1:1 + _half]
    M4 = sys.argv[1 + _half:]
else:
    M0 = ['mid250_base', 'mid1', 'lath1']
    M4 = ['mid250_ns4', 'mid192_ns4', 'lath192_ns4', 'mid192_s2_ns4']


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return float('nan')


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
    st = np.arange(len(rows), dtype=float) * ev
    W = np.array([fnum(r, 'W_cal') for r in rows])
    T = np.array([fnum(r, 'T_cal') for r in rows])
    g1 = np.array([fnum(r, 'box_touch') for r in rows]) <= 0
    g2 = np.array([fnum(r, 'ncomp') for r in rows]) <= 1
    good = g1 & g2 & np.isfinite(W) & np.isfinite(T)
    return st, W, T, good


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0]))


def curve(d):
    o = load(d)
    if o is None:
        return {}
    st, W, T, good = o
    base = st[I0]
    out = {}
    for hi in range(60, int(st[-1]) + 1, 20):
        m = good & (st >= base) & (st <= hi)
        if int(m.sum()) < 8:
            continue
        t = st[m]
        sW, eW = fit(t, W[m])
        sT, eT = fit(t, T[m])
        if sW <= 0 or sT <= 0:
            continue
        r = sW / sT
        out[hi] = (r, r * np.sqrt((eW / sW) ** 2 + (eT / sT) ** 2), int(m.sum()))
    return out


C = {d: curve(d) for d in M0 + M4}
print('=' * 104)
print('S-1 逐臂逐窗口 `ΔW:ΔT`（设计 = **%.4f**）' % DESIGN)
print('=' * 104)
his = sorted({h for d in C for h in C[d]})
hdr = '%-7s' % 'hi' + ''.join('%15s' % (d[:13]) for d in M0 + M4)
print(hdr)
for hi in his:
    line = '%-7d' % hi
    for d in M0 + M4:
        v = C[d].get(hi)
        line += '%15s' % (('%.3f' % v[0]) if v else '—')
    print(line)

print('\n' + '=' * 104)
print('S-2/S-3 **共同窗口**上 m=0 组 vs m=4 组（同 `hi` 相比才合法）')
print('=' * 104)
print('%-7s %28s %28s %s' % ('hi', 'A 组（[设计比]）', 'B 组（[设计比]）', '区间重叠?'))
for hi in his:
    a = [C[d][hi][0] for d in M0 if hi in C[d]]
    b = [C[d][hi][0] for d in M4 if hi in C[d]]
    if len(a) < 2 or len(b) < 2:
        continue
    ov = not (max(a) < min(b) or max(b) < min(a))
    print('%-7d %28s %28s %s'
          % (hi, '[%.2f–%.2f]' % (min(a) / DESIGN, max(a) / DESIGN),
             '[%.2f–%.2f]' % (min(b) / DESIGN, max(b) / DESIGN),
             '**重叠 ⇒ 分不开**' if ov else '不重叠 ⇒ 差异真实'))
print('\n⇒ 判读：若在**共同窗口**上两组区间**重叠** ⇒ B-18 的"m=0 更接近设计"**是窗口效应**，')
print('   应撤回该表述；若**始终不重叠** ⇒ 差异真实，须查 `norm_smooth` 对**相对**各向异性的影响。')
print('=' * 104)
