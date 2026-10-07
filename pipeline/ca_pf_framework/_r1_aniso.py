#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_aniso.py --- ★ 各向异性比值的**有效窗口**读数（替代"单一斜率"口径）

为什么要换口径（两条实测，见台账 B-1b / B-1c）
----------------------------------------------
1. **速率比随窗口漂移**：`mid250_ns4` 的 `ΔW:ΔL` 从 0.072 单调升到 0.114；
   而回归 σ 从 0.042 **缩到 0.002**（长窗口 = **假精度**）。
   ⇒ 任何"`ΔW:ΔL`=0.098 ≈ 设计 0.10"式的**单值断言不可用**。
2. **长窗口会被守卫污染**：
   * **G-1 盒壁**：`mid250_ns4` 在 **step ≥360 触壁**（L=19.6→23.3 µm，占 24 µm 盒子的 97%）
     ⇒ 那些步的形貌读数**无效**（`_r1_exp.py:41`）；
   * **G-2 碎片**：`ncomp>1` ⇒ `max−min` 被碎片绑架（`_r1_exp.py:42`）。

本脚本只报**通过两道守卫**的窗口，并显式给出"最后一个有效窗口"。
"""
import csv
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
DESIGN = dict(W=0.100, T=0.030)          # 设计 1 : 0.100 : 0.030（β_h=3.5, β_w=2.3）
DEFAULT = ['mid250_ns4', 'mid250_base', 'mid192_ns4', 'mid192_s2_ns4',
           'lath192_ns4', 'lath1', 'mid1']


def fnum(r, k):
    try:
        return float(r[k])
    except (TypeError, ValueError, KeyError):
        return float('nan')


def load(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    every = 4.0
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            every = float(np.median(np.diff(mk)))
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    nseed = None
    if os.path.exists(mp):
        try:
            nseed = json.load(open(mp)).get('nseed')
        except Exception as e:                                   # noqa: BLE001
            # ⚠ 记账：这里原来写的是 `except Exception: pass` —— 它**吞掉了**
            #   `json` 没 import 造成的 `NameError`，于是 `nseed` 静默为 None，
            #   多核臂的"拒绝运行"守卫**看起来装好了却从不触发**。
            #   （这正是 `AGENTS.md §3.4`「守卫静默失效」的同一类错。）
            #   ⇒ 改成**显式告警**，绝不静默。
            print('   ⚠ 读不到 %s 的 nseed（%s：%s）⇒ 无法判断单核/多核，'
                  '按**单核**规则处理' % (d, type(e).__name__, e))
    rows = list(csv.DictReader(open(os.path.join(HERE, '_exp', d, 'series.csv'))))
    st = np.arange(len(rows), dtype=float) * every
    c = {k: np.array([fnum(r, k) * 1e9 for r in rows])
         for k in ('L_cal', 'W_cal', 'T_cal')}
    if nseed is not None and nseed > 1:
        # ★★ 见台账 B-6：多核算例里 `ncomp>1` 是**目标状态**（多个核），
        #   不是污染 ⇒ 本脚本的"单核 G-2 剔除"规则**不适用**，必须拒绝运行，
        #   否则会把**每一步**都剔掉（实测 `e7_selfac` 27/27 步被剔）。
        return dict(error='多核臂（nseed=%s）：本脚本的 G-2 剔除规则不适用，'
                          '请用 `_r1_analyze.py --block` 的逐分量量具' % nseed)
    g2 = np.array([not np.isfinite(fnum(r, 'ncomp')) or fnum(r, 'ncomp') == 1.0
                   for r in rows])
    g1 = np.array([not np.isfinite(fnum(r, 'box_touch')) or fnum(r, 'box_touch') == 0
                   for r in rows])
    return st, c, (g1 & g2), g1, g2, every


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(r @ r) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0]))


def ratio(t, a, b):
    sa, ea = fit(t, a)
    sb, eb = fit(t, b)
    if sb <= 0 or sa == 0:
        return np.nan, np.nan
    r = sa / sb
    return r, abs(r) * np.sqrt((ea / sa) ** 2 + (eb / sb) ** 2)


def report(d):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('\n%-16s ✗ 无 series.csv' % d); return
    ld = load(d)
    if isinstance(ld, dict) and 'error' in ld:
        print('\n%-16s ⛔ %s' % (d, ld['error'])); return
    st, c, good, g1, g2, every = ld
    if len(st) < 12:
        print('\n%-16s ✗ 行数不足 (%d)' % (d, len(st))); return
    print('\n' + '-' * 94)
    print('%s   n=%d  step 0…%g  every=%g' % (d, len(st), st[-1], every))
    print('   守卫：G-1 盒壁剔除 %d 步；G-2 碎片剔除 %d 步；**合计有效 %d/%d**'
          % (int((~g1).sum()), int((~g2).sum()), int(good.sum()), len(st)))
    lastvalid = st[good].max() if good.any() else None
    if lastvalid is not None and lastvalid < st[-1]:
        print('   ⇒ ⚠ 有效数据止于 **step %g**（其后被守卫剔除，不得参与拟合）'
              % lastvalid)
    print('   %8s %5s %15s %15s' % ('窗口右端', 'n', 'ΔW:ΔL', 'ΔT:ΔL'))
    base = st[8]
    rows_out = []
    for hi in range(80, int(st[-1]) + 1, 40):
        m = (st >= base) & (st <= hi) & good
        if int(m.sum()) < 8:
            continue
        t = st[m]
        rw, sw = ratio(t, c['W_cal'][m], c['L_cal'][m])
        rt, stt = ratio(t, c['T_cal'][m], c['L_cal'][m])
        rows_out.append((hi, int(m.sum()), rw, sw, rt, stt))
        print('   %8d %5d %9.4f±%-5.3f %9.4f±%-5.3f'
              % (hi, int(m.sum()), rw, sw, rt, stt))
    if not rows_out:
        print('   ✗ 无任何有效窗口'); return
    hi, n, rw, sw, rt, stt = rows_out[-1]
    print('   ⇒ **最后一个有效窗口**：step ∈ [%g, %g]（n=%d）'
          % (base, st[good].max(), n))
    print('     ΔW:ΔL = **%.4f±%.3f**（设计 %.3f ⇒ **%.2f×**）'
          % (rw, sw, DESIGN['W'], rw / DESIGN['W']))
    print('     ΔT:ΔL = **%.4f±%.3f**（设计 %.3f ⇒ **%.2f×**）'
          % (rt, stt, DESIGN['T'], rt / DESIGN['T']))
    print('     本臂内的**总漂移**：ΔW:ΔL %.4f → %.4f（%.0f%%）'
          % (rows_out[0][2], rw, 100 * (rw - rows_out[0][2])
             / max(abs(rows_out[0][2]), 1e-30)))


for d in (sys.argv[1:] or DEFAULT):
    report(d)
print('\n' + '=' * 94)
print('⚠ 报任何"速率比与设计一致"的结论时，必须同时给出：')
print('   **臂名 + 有效窗口 + 该窗口的 σ + 本臂内的漂移幅度**。禁止只报一个数。')
print('=' * 94)
