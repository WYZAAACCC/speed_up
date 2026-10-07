#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_dxdegenerate.py --- ★★ 核查：`mid250_ns4` 与 `mid192_ns4` 是不是**同一个胞级计算**？

起因
----
`_r1_dxcurve.py` 里两臂的 `ΔW:ΔL` 在 4/6 个窗口上**连 σ 都完全相同**
（0.072±0.042 / 0.038±0.022 / 0.083±0.021 / 0.086±0.010）。
若两臂是"同一个胞级动力学、只是物理标尺不同"，这是**必然**结果。

算术（读 `meta.json`）
----------------------
  `mid250_ns4`：Δx=250 nm，`seed_scale=2` ⇒ 种子 4000×1600×640 nm = **16.0 / 6.4 / 2.56 胞**
  `mid192_ns4`：Δx=125 nm，`seed_scale=1` ⇒ 种子 2000× 800×320 nm = **16.0 / 6.4 / 2.56 胞**
⇒ **胞数完全相同**。而 `dt = 0.15·Δx/(MOB·DF)` 也按 Δx 等比缩放
   ⇒ **每步的"胞位移"都是 0.15 胞** ⇒ 两臂在**胞单位**下应当逐步逐位相同。

判据
----
  J-1 两臂的 `L_cal` 是否**严格成比例**（比值是否为常数 0.5，逐行检查）；
  J-2 若成立 ⇒ 两臂是**同一个计算**，`_r1_dxconsist.py` 的那个对照**是重言式**，
      对"物理是否依赖 Δx"**不提供任何证据**；
  J-3 因此**有信息量的 Δx 对照只有** `mid250_ns4`（16/6.4/2.56 胞）
      vs `mid192_s2_ns4`（**32/12.8/5.12 胞**，同一物理尺寸）。
"""
import csv
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = [('mid250_ns4', 'mid192_ns4'), ('mid250_ns4', 'mid192_s2_ns4'),
         ('mid250_base', 'mid1')]


def cfg(d):
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    if not os.path.exists(mp):
        return {}
    try:
        return json.load(open(mp))
    except Exception:                                                # noqa: BLE001
        return {}


def col(d, k):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    out = []
    for r in csv.DictReader(open(p)):
        try:
            out.append(float(r[k]))
        except (TypeError, ValueError, KeyError):
            out.append(np.nan)
    return np.array(out)


print('=' * 100)
print('J-0 两臂的**胞级**种子尺寸（决定它们是不是同一个计算）')
print('=' * 100)
print('%-16s %6s %8s %8s %14s %22s' %
      ('臂', 'N', 'Δx(nm)', 'scale', '物理 L/W/T(nm)', '胞级 L/W/T'))
for d in ['mid250_ns4', 'mid192_ns4', 'mid192_s2_ns4', 'mid250_base', 'mid1']:
    m = cfg(d)
    if not m:
        print('%-16s （无 meta）' % d); continue
    sh = m.get('shape', {})
    dx = m.get('dx_nm') or 125.0
    L, W, T = sh.get('L'), sh.get('W'), sh.get('T')
    if L is None:
        print('%-16s %6s %8s %8s  （形状非棱柱）' % (d, m.get('N'), dx,
                                                    m.get('seed_scale')))
        continue
    print('%-16s %6s %8s %8s %14s %22s'
          % (d, m.get('N'), dx, m.get('seed_scale'),
             '%.0f/%.0f/%.0f' % (L, W, T),
             '%.2f/%.2f/%.2f' % (L / dx, W / dx, T / dx)))

print('\n' + '=' * 100)
print('J-1 两臂 `L_cal` 是否严格成比例（逐行）')
print('=' * 100)
for A, B in PAIRS:
    pa = os.path.join(HERE, '_exp', A, 'series.csv')
    pb = os.path.join(HERE, '_exp', B, 'series.csv')
    if not (os.path.exists(pa) and os.path.exists(pb)):
        print('%-32s ✗ 缺数据' % ('%s vs %s' % (A, B))); continue
    a, b = col(A, 'L_cal'), col(B, 'L_cal')
    n = min(len(a), len(b))
    m = np.isfinite(a[:n]) & np.isfinite(b[:n]) & (a[:n] > 0)
    if m.sum() < 5:
        print('%-32s ✗ 有效行不足' % ('%s vs %s' % (A, B))); continue
    rt = b[:n][m] / a[:n][m]
    exact = float(np.ptp(rt)) == 0.0 or float(np.ptp(rt)) < 1e-12
    print('%-32s n=%-4d  比值 = %.10f … %.10f  极差 %.3e  ⇒ %s'
          % ('%s vs %s' % (A, B), int(m.sum()), rt.min(), rt.max(),
             float(np.ptp(rt)),
             '**严格成比例 ⇒ 同一个胞级计算**' if exact else '不成比例（各自独立）'))
print('\n' + '=' * 100)
print('J-2/J-3 结论：')
print('  * 若某一对的 `L_cal` 严格成比例（比值恒定）⇒ 两臂在**胞单位下是同一个计算**，')
print('    Δx 只改物理标尺 ⇒ 该对照对"物理是否依赖 Δx"**是重言式，不提供证据**。')
print('  * 有信息量的对照只有**物理尺寸相同、胞数不同**的那一对')
print('    （`mid250_ns4` 16/6.4/2.56 胞 vs `mid192_s2_ns4` 32/12.8/5.12 胞）。')
print('=' * 100)
