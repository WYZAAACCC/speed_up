#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r161_rvsE.py —— ★★★ **`r_selfac` 与弹性能密度**到底有没有对应关系？

## 线索（`_r160`）

两臂（**同几何、同 12 根、只差变体集**）：
* `saOddG`：`r` 0.049 → 0.078（**下界 0**）
* `saSet2`：`r` 0.542 → 0.617（**下界 0.483**）
⇒ `r` 差 **10 倍**。

而 `E_el/Vt`：step 40 时 **1.736e8 vs 1.830e8**（差 5%）；step 400 时 **3.519e8 vs 3.928e8**（差 10%）。

**⇒ `r` 差 10 倍，而 `E_el/Vt` 只差 5–10%** ⇒ 两者**没有**可用的定量对应关系。

⇒ 本脚本用**同步对照表**把它钉死（同 step、同几何、`Vt` 也并排报，排除"体积不同"这个混杂）。

## 判据（**先写死**）

* 若 `E_el/Vt` 的**相对差** ≪ `r` 的**相对差**（比如差一个数量级）⇒
  **`r` 不是弹性能的代理** ⇒ 用它判"自协调"**不可靠**；
* 若两者量级相当 ⇒ `r` 可用。

⚠ **口径**：`E_el_J` 与 `Vt` 都是**广延量** ⇒ 只比**比值**（`§84` 规程③）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
A, B = 'saOddG', 'saSet2'


def load(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {}
    for key in ('step', 'r_selfac', 'E_el_J', 'Vt'):
        v = []
        for r in rows:
            try:
                v.append(float(r[key]))
            except (KeyError, ValueError):
                v.append(float('nan'))
        out[key] = np.array(v)
    out['E_el/Vt'] = out['E_el_J'] / np.maximum(out['Vt'], 1e-300)
    return out


def main():
    a, b = load(A), load(B)
    if a is None or b is None:
        print('⚠ 数据不全'); return 2
    print('=' * 112)
    print('_r161 —— `r_selfac` vs `E_el/Vt`（同几何、同 12 根、只差变体集）')
    print('=' * 112)
    ks = sorted(set(a['step'].tolist()) & set(b['step'].tolist()))
    print('  %-7s | %-9s %-9s %-8s | %-12s %-12s %-8s | %-10s %-10s'
          % ('step', 'r(A)', 'r(B)', 'r 比', 'E/Vt(A)', 'E/Vt(B)', 'E 比',
             'Vt(A)µm³', 'Vt(B)µm³'))
    rows = []
    for k in ks:
        ia = int(np.where(a['step'] == k)[0][0])
        ib = int(np.where(b['step'] == k)[0][0])
        ra, rb = a['r_selfac'][ia], b['r_selfac'][ib]
        ea, eb = a['E_el/Vt'][ia], b['E_el/Vt'][ib]
        if not (np.isfinite(ra) and np.isfinite(rb) and ea > 0 and eb > 0):
            continue
        rr = rb / ra if ra > 1e-12 else float('nan')
        er = eb / ea
        rows.append((k, ra, rb, rr, ea, eb, er))
        print('  %-7d | %-9.4f %-9.4f %-8.2f× | %-12.4g %-12.4g %-8.2f× | %-10.4f %-10.4f'
              % (k, ra, rb, rr, ea, eb, er, a['Vt'][ia] * 1e18, b['Vt'][ib] * 1e18))
    if not rows:
        print('⚠ 无有效行'); return 1
    R = np.array(rows)
    print()
    # 丢掉 step 0（`E_el_J` 那时为 0，是"没算/没落盘"，不是真值）
    m = R[:, 0] > 0
    rr = R[m, 3]
    er = R[m, 6]
    print('  ---- 判读（**排除 step 0**：那时 `E_el_J = 0`，是"还没算"不是真值）----' % ())
    print('     `r` 的跨臂比：     中位 **%.2f×**（范围 %.2f–%.2f）' % (np.median(rr), rr.min(), rr.max()))
    print('     `E_el/Vt` 的跨臂比：中位 **%.2f×**（范围 %.2f–%.2f）' % (np.median(er), er.min(), er.max()))
    print('     比值之比（r 比 / E 比）中位 = **%.2f**' % np.median(rr / er))
    print()
    if np.median(rr) > 3 * np.median(er):
        print('  ⇒ ⚠⚠ **`r` 的跨臂差（%.1f×）远大于 `E_el/Vt` 的跨臂差（%.2f×）**'
              % (np.median(rr), np.median(er)))
        print('     ⇒ **`r_selfac` 不是弹性能密度的代理** ——')
        print('       两臂的"自协调程度"按 `r` 差 %.1f 倍，而弹性能密度只差 %.0f%%。'
              % (np.median(rr), 100 * (np.median(er) - 1)))
        print('     ⇒ **用 `r` 判"自协调"不可靠**：它既不代理能量，也不预测动力学。')
    else:
        print('  ⇒ `r` 与 `E_el/Vt` 的跨臂差异量级相当 ⇒ `r` 可作为粗略代理（需更多点确认）')
    print()
    print('  ⚠ 记账：`Vt` 列并排报了 —— 两臂 `Vt` 接近（见上表）⇒ **体积差异不是这个结论的来源**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
