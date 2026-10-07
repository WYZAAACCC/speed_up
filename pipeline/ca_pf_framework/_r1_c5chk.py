#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_c5chk.py --- ★ C-5（`fill_cal ≥ 0.70`）到底在量什么？它能不能当验收判据？

背景
----
C-5 是 `_r1_analyze.py` 的六条判据之一，用途写的是「区分板条/板 与 纺锤/针」。
但本轮用**有效窗口**口径重看，它**在单核臂上普遍 FAIL**，而且**随分辨率变**：

| 臂 | Δx | `fill_cal` 初 → 末 |
|---|---|---|
| `mid1`       | ? | 1.030 → **0.718**（PASS） |
| `mid192_ns4` | 125 | 1.030 → **0.499**（FAIL） |

`fill_cal = V/(L·W·T)` 的**几何含义**：它等于"体积占自己外接盒的比例"。
  * **长方体（棱柱）= 1.000**；
  * **椭球 = π/6 = 0.524**。
⇒ 所以 `fill_cal` 量的**不是长宽比**，而是**"有多方"（面的平直度/棱角）**。
   一个**圆角板**（尖端与棱都圆）会给出 ≈0.5，而它在长宽比上完全可以是板条。

判据
----
  E-1 报出各臂 `fill_cal` 的**单调性**（是否随步下降）与**末值**；
  E-2 报出**同形状、不同 Δx** 的 `fill_cal` 差异 ⇒ 若差异大，则 C-5 **与分辨率耦合**；
  E-3 给出参考值：长方体 1.000、椭球 0.524 ⇒ 判断测到的形状更接近哪一个。
"""
import csv
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')
ARMS = ['mid1', 'mid192_ns4', 'mid192_s2_ns4', 'mid250_ns4', 'mid250_base',
        'lath1', 'lath192_ns4', 'equi192_ns4', 'e5_equi6']


def fnum(r, k):
    try:
        v = float(r[k])
        return v if np.isfinite(v) else np.nan
    except (TypeError, ValueError, KeyError):
        return np.nan


def every_of(d):
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    if os.path.exists(lp):
        mk = [int(m.group(1)) for m in
              (PAT.match(l) for l in open(lp, errors='replace')) if m]
        if len(mk) > 2:
            return float(np.median(np.diff(mk)))
    return 4.0


print('=' * 100)
print('参考值：**长方体 = 1.000**，**椭球 = π/6 = %.3f**' % (np.pi / 6))
print('=' * 100)
print('%-16s %6s %6s %8s %10s %10s %9s %s'
      % ('臂', 'N', 'Δx', 'nseed', 'fill_cal初', 'fill_cal末', '单调?', '末值更接近'))
print('-' * 100)
rows_out = []
for d in ARMS:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p)))
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    N = dx = nseed = None
    if os.path.exists(mp):
        try:
            m = json.load(open(mp))
            N, dx, nseed = m.get('N'), m.get('dx_nm'), m.get('nseed')
        except Exception:                                        # noqa: BLE001
            pass
    fc = np.array([fnum(r, 'fill_cal') for r in rows])
    if not np.isfinite(fc).any():
        L = np.array([fnum(r, 'L_cal') for r in rows])
        W = np.array([fnum(r, 'W_cal') for r in rows])
        T = np.array([fnum(r, 'T_cal') for r in rows])
        V = np.array([fnum(r, 'V') for r in rows])
        fc = V / np.maximum(L * W * T, 1e-30)
    v = fc[np.isfinite(fc)]
    if v.size < 3:
        continue
    # 单调性：用秩相关（对噪声稳健）
    idx = np.arange(v.size, dtype=float)
    ri = np.argsort(np.argsort(idx)).astype(float)
    rv = np.argsort(np.argsort(v)).astype(float)
    ri -= ri.mean(); rv -= rv.mean()
    rho = float(ri @ rv / np.sqrt((ri @ ri) * (rv @ rv)))
    near = '椭球(0.524)' if abs(v[-1] - 0.524) < abs(v[-1] - 1.0) else '长方体(1.000)'
    print('%-16s %6s %6s %8s %10.3f %10.3f %9.2f %s'
          % (d, N, dx, nseed, v[0], v[-1], rho, near))
    rows_out.append((d, N, dx, nseed, v[0], v[-1], rho))

print('-' * 100)
print('判读：')
for tag, sel in (('单核 mid', lambda r: r[0] in ('mid1', 'mid192_ns4', 'mid192_s2_ns4')),
                 ('单核 lath', lambda r: r[0] in ('lath1', 'lath192_ns4'))):
    s = [r for r in rows_out if sel(r)]
    if len(s) >= 2:
        mx, mn = max(r[5] for r in s), min(r[5] for r in s)
        print('  * **%s**：末值 %.3f … %.3f（差 %.3f，跨 %s）'
              % (tag, mn, mx, mx - mn,
                 '/'.join(str(r[2]) for r in s)))
print('  * 若**同形状不同 Δx** 的 `fill_cal` 差得远 ⇒ C-5 **与分辨率耦合**，')
print('    不能当"与分辨率无关"的验收判据。')
print('  * `fill_cal` 量的是**面的平直度**，不是**长宽比** ⇒')
print('    长宽比验收请看 `_r1_aniso.py` 的 `ΔW:ΔL`/`ΔT:ΔL`。')
print('=' * 100)
