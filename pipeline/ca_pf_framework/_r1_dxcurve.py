#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_dxcurve.py --- ★★ Δx 无关性的**正确检验**：比"漂移曲线"，不比"单点标量"

为什么换口径（台账 B-1b / B-1d）
--------------------------------
速率比**不是常数**：`mid250_ns4` 的 `ΔW:ΔL` 随窗口从 0.072 单调升到 0.114（+56%）。
在此前提下，`_r1_dxconsist.py` 的"各取一个标量再比"有两个毛病：
  * 标量**依赖窗口** ⇒ 两臂用了不同窗口时，比出来的是"窗口差"而非"Δx 差"；
  * 只用了**一个**窗口的信息 ⇒ 统计功效低（实测相对不确定度 27%）。

正确做法
--------
把每个臂看成一条**曲线** `f_arm(hi)`（`hi` = 窗口右端），然后问：
**两条曲线在共同窗口内是否重合？**（同一 `hi` 下逐点比较，再做合并检验）
  * 用**配对差** `d(hi) = r_B(hi) − r_A(hi)`：若 Δx 无影响 ⇒ `d(hi)` 应在 0 附近、
    且**不随 `hi` 单调漂移**（单调漂移是系统差，不是噪声）；
  * 报 `mean(d)/σ_d` 与 `d(hi)` 的**线性趋势斜率**；
  * **自由度为窗口数**，比单点比较有力得多。

判据
----
  K-1 逐窗口配对差 `d(hi)` ± σ；
  K-2 合并 z = `mean(d)/sem(d)`（配对 ⇒ 消掉两臂共有的漂移）；
  K-3 **趋势检验**：`d(hi)` 对 `hi` 的斜率是否显著非零（显著 ⇒ 有 Δx 耦合）；
  K-4 有效率对比：曲线口径 vs 单点口径的不确定度。
"""
import csv
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
I0 = 8


def every_of(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            return float(np.median(np.diff(mk)))
    return 4.0


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
    ev = every_of(d)
    st = np.arange(len(rows), dtype=float) * ev
    L = np.array([fnum(r, 'L_cal') for r in rows])
    W = np.array([fnum(r, 'W_cal') for r in rows])
    T = np.array([fnum(r, 'T_cal') for r in rows])
    g1 = np.array([fnum(r, 'box_touch') for r in rows]) <= 0
    g2 = np.array([fnum(r, 'ncomp') for r in rows]) <= 1
    good = g1 & g2 & np.isfinite(L) & np.isfinite(W) & np.isfinite(T)
    return st, L, W, T, good


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0]))


def ratio_curve(d, his, num, den):
    """对每个窗口右端 `hi` 返回 `Δnum:Δden` ± σ（窗口左端固定 = 第 `I0` 个采样）。"""
    o = load(d)
    if o is None:
        return None
    st, L, W, T, good = o
    col = {'L': L, 'W': W, 'T': T}
    base = st[I0] if len(st) > I0 else st[0]
    out = []
    for hi in his:
        m = good & (st >= base) & (st <= hi)
        if int(m.sum()) < 8:
            out.append((hi, np.nan, np.nan, 0))
            continue
        t = st[m]
        sa, ea = fit(t, col[num][m])
        sb, eb = fit(t, col[den][m])
        if sb <= 0 or sa == 0:
            out.append((hi, np.nan, np.nan, int(m.sum())))
            continue
        r = sa / sb
        s = abs(r) * np.sqrt((ea / sa) ** 2 + (eb / sb) ** 2)
        out.append((hi, r, s, int(m.sum())))
    return out


ARMS = sys.argv[1:] or ['mid250_ns4', 'mid192_ns4', 'mid192_s2_ns4']
data = {}
for d in ARMS:
    o = load(d)
    if o is None:
        print('%-16s ✗ 无数据' % d); continue
    data[d] = o
    print('%-16s n=%-4d step 0…%g  有效 %d'
          % (d, len(o[0]), o[0][-1], int(o[4].sum())))
if len(data) < 2:
    print('✗ 臂数不足'); sys.exit(0)

hi_max = int(min(v[0][-1] for v in data.values()))
his = list(range(80, hi_max + 1, 20))
if len(his) < 3:
    print('⚠ 共同窗口太短（hi_max=%d）⇒ 无法做趋势检验' % hi_max)

print('\n' + '=' * 100)
print('K-1/K-2/K-3  逐窗口 `ΔW:ΔL` 及**配对差**（配对可消掉两臂共有的漂移）')
print('=' * 100)
curves = {d: ratio_curve(d, his, 'W', 'L') for d in data}
hdr = '%-8s' % 'hi' + ''.join('%16s' % d[:14] for d in data)
print(hdr)
for i, hi in enumerate(his):
    line = '%-8d' % hi
    for d in data:
        _, r, s, n = curves[d][i]
        line += '%16s' % (('%.3f±%.3f' % (r, s)) if np.isfinite(r) else '—')
    print(line)

if len(data) == 2:
    A, B = list(data)
    ds, ses, hh = [], [], []
    for i, hi in enumerate(his):
        ra, sa, _ = curves[A][i][1], curves[A][i][2], curves[A][i][3]
        rb, sb = curves[B][i][1], curves[B][i][2]
        if np.isfinite(ra) and np.isfinite(rb):
            ds.append(rb - ra)
            ses.append(float(np.hypot(sa, sb)))
            hh.append(hi)
    if len(ds) >= 3:
        ds = np.array(ds); ses = np.array(ses); hh = np.array(hh, float)
        w = 1.0 / np.maximum(ses, 1e-30) ** 2
        dm = float((ds * w).sum() / w.sum())
        sem = float(1.0 / np.sqrt(w.sum()))
        print('\nK-2 加权平均配对差 = **%+.4f ± %.4f**  ⇒  z = %+.2f'
              % (dm, sem, dm / max(sem, 1e-30)))
        print('    ⇒ %s' % ('一致（|z|<2）⇒ 两臂**同一条曲线**' if abs(dm / sem) < 2
                           else '不一致（|z|≥2）⇒ 存在 Δx 耦合'))
        # 趋势
        Aw = np.vstack([hh, np.ones_like(hh)]).T
        sol, *_ = np.linalg.lstsq(Aw, ds, rcond=None)
        res = ds - Aw @ sol
        dof = max(len(ds) - 2, 1)
        s2 = float(res @ res) / dof
        cov = s2 * np.linalg.inv(Aw.T @ Aw)
        slope, esl = float(sol[0]), float(np.sqrt(cov[0, 0]))
        print('K-3 配对差对窗口的**趋势** = %+.3e ± %.3e /步  ⇒  %s'
              % (slope, esl,
                 '无显著趋势（|斜率|<2σ）⇒ 差是噪声' if abs(slope) < 2 * esl
                 else '**显著趋势** ⇒ 两臂曲线不平行 ⇒ **有 Δx 耦合**'))
        # K-4 功效
        s_sp = float(np.mean(ses))
        print('K-4 功效：单点口径 σ=%.4f ；曲线口径（配对）σ=%.4f  ⇒ 提升 **%.1f×**'
              % (s_sp, sem, s_sp / max(sem, 1e-30)))
print('=' * 100)
print('⚠ 记账：仅有 2 个 Δx；本检验回答的是"两条曲线是否重合"，')
print('   比单点标量有力，但**仍不能**替代第三个 Δx 点。')
print('=' * 100)
