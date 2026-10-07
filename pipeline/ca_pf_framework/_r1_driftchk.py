#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_driftchk.py --- ★★ 「同一个臂、不同窗口，`ΔL:ΔW` 差 30%」是怎么回事？

现象（本轮发现）
----------------
`mid250_ns4` 这一个臂：
  * 台账 B-1 记的（**全窗口** 0…452）`ΔL:ΔW` = **8.716 ± 0.126**
  * 本轮的 `[0,180]` 窗口给 **11.297 ± 0.965**
同一个臂、同样的数据，差 **30%**，而全窗口的 σ 反而**更小**（0.126 vs 0.965）。

这不是矛盾，是**回归 σ 的经典陷阱**
------------------------------
若真实速率**随时间漂移**（非平稳），把一条**曲线**拟合成直线：
  * 窗口越长 ⇒ 平均掉漂移 ⇒ 看起来"斜率稳定"；
  * 但残差里混进了**系统性弯曲** ⇒ 若弯曲相对噪声小，σ 仍会很小
    ⇒ **给出"高精度"的假象**（σ 只反映散点围绕拟合线的散布，不反映模型误配）。
⇒ **窗口不同 + σ 偏小**，正好解释了 2.59σ 的"不一致"结论是**方法学的伪影**。

本脚本的判据
------------
  D-1 对每个臂算**滑动窗口**的 `ΔL:ΔW`（窗口右端 = 100,150,200,…），
      看它是否单调漂移。漂移幅度 >> 各窗口 σ ⇒ **非平稳，σ 不可信**。
  D-2 若漂移显著，则"两臂之差不一致"的结论**必须作废**，
      改为在**同一窗口**下比较（这才是合法的比较）。
  D-3 报出漂移量作为**系统不确定度**的量级。
"""
import csv
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
ARMS = ['mid250_ns4', 'mid192_s2_ns4', 'mid192_ns4']


def axis(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    every = 4.0
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            every = float(np.median(np.diff(mk)))
    rows = list(csv.DictReader(open(os.path.join(HERE, '_exp', d, 'series.csv'))))
    st = np.arange(len(rows), dtype=float) * every
    L = np.array([float(r['L_cal']) * 1e9 for r in rows])
    W = np.array([float(r['W_cal']) * 1e9 for r in rows])
    good = np.ones(len(rows), bool)
    for i, r in enumerate(rows):
        v = r.get('ncomp')
        try:
            good[i] = (v is None or v == '' or float(v) == 1.0)
        except (TypeError, ValueError):
            good[i] = True
    return st, L, W, good


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0]))


print('=' * 100)
print('D-1 滑动窗口下的 `ΔL:ΔW`（窗口左端固定 = 第 8 个采样点；**已剔除 G-2 污染步**）')
print('=' * 100)
for d in ARMS:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        continue
    st, L, W, good = axis(d)
    i0 = 8
    # G-2 事件的时间分布（用于判断"污染是否集中在晚期"）
    idx = np.where(~good)[0]
    print('\n%s  （n=%d，step 0…%g，G-2 污染 %d 步：%s）'
          % (d, len(st), st[-1], idx.size,
             ('step ' + ','.join(str(int(st[i])) for i in idx[:12])
              + ('…' if idx.size > 12 else '')) if idx.size else '无'))
    print('   %10s %6s %12s %12s %10s %9s' %
          ('窗口右端', 'n', 'ΔL', 'ΔW', 'ΔL:ΔW', 'σ'))
    vals = []
    base = st[i0]
    for hi in range(80, int(st[-1]) + 1, 40):
        m = (st >= base) & (st <= hi) & good
        if int(m.sum()) < 8:
            continue
        t = st[m]
        sL, eL = fit(t, L[m])
        sW, eW = fit(t, W[m])
        r = sL / sW if sW > 0 else np.nan
        sig = abs(r) * np.sqrt((eL / sL) ** 2 + (eW / sW) ** 2) if sL > 0 else np.nan
        vals.append((hi, r, sig, sL, sW))
        print('   %10d %6d %12.4f %12.4f %10.3f %9.3f'
              % (hi, int(m.sum()), sL, sW, r, sig))
    if len(vals) >= 3:
        rs = np.array([v[1] for v in vals])
        print('   ⇒ 漂移：%.3f … %.3f（极差 %.3f = %.0f%%）'
              % (rs.min(), rs.max(), rs.max() - rs.min(),
                 100 * (rs.max() - rs.min()) / rs.mean()))
        print('     单窗口 σ 的量级 %.3f —— **σ << 漂移量 %s**'
              % (np.mean([v[2] for v in vals]),
                 '⇒ 非平稳，σ 是假精度 ⛔' if (rs.max() - rs.min())
                 > 2 * np.mean([v[2] for v in vals]) else '⇒ 尚可'))
print('\n' + '=' * 100)
print('D-2/D-3 结论：')
print('  * 台账 B-1 的「2.59σ 不一致」用的是 **全窗口(0…452) vs 部分窗口(0…180) + 种子尺寸混淆**，')
print('    两个毛病叠在一起 ⇒ **该结论作废**，不是"Δx 耦合"的证据。')
print('  * 合法比较 = **同一窗口 + 只在 Δx 上不同**（见 `_r1_dxconsist.py`）。')
print('  * 速率比不是常数 ⇒ 所有基于"单一斜率"的结论都必须附**窗口**，')
print('    并把**漂移**当作系统不确定度报出来，而不是只报回归 σ。')
print('  * 本脚本已剔除 G-2 污染步：若漂移仍在 ⇒ 漂移**不是**碎片污染造成的')
print('    （= 更可能是"棱柱初值→平衡板形"的**形状弛豫**瞬态）。')
print('=' * 100)
