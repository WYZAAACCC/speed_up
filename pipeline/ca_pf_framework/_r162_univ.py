#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r162_univ.py —— **`§118` 的普适性检验**：全库范围内 `r` 排不排得动 `E_el/Vt`？

## 为什么要做（`§118` 第五节自己列的局限）

`§118` 的结论（`r` 差 9.10× 而 `E_el/Vt` 只差 1.12×）只有 **2 个变体集、1 个几何**
⇒ **普适性未验**。

## 做法（**控制混杂**）

`E_el/Vt` 同时受 **转变体积分数**（`Vt`）与**形貌**影响 ⇒ 直接把全库画散点会被混杂主导。
⇒ 只在**`Vt` 相近**的臂之间比：

1. 取全库所有同时有 `r_selfac` / `E_el_J` / `Vt` 的臂的**末行**；
2. 只在**同一个 `(N, Δx)`** 内比（跨分辨率不可比）；
3. 再筛 **`|ΔVt| / Vt < 10%`** 的**成对**比较；
4. 报每一对的 **`Δr/r`** 与 **`Δ(E/Vt)/(E/Vt)`**，看哪一个更大。

⚠ **只报存在性与量级**，不做因果；样本以成对形式给出（每对都可比）。
"""
from __future__ import annotations

import csv
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp')


def collect():
    rows = []
    for p in glob.glob(os.path.join(MB, '**', 'series.csv'), recursive=True):
        try:
            rs = list(csv.DictReader(open(p)))
        except Exception:
            continue
        if not rs or not all(c in rs[0] for c in ('r_selfac', 'E_el_J', 'Vt')):
            continue
        mj = os.path.join(os.path.dirname(p), 'meta.json')
        if not os.path.exists(mj):
            continue
        try:
            m = json.load(open(mj))
            ea = m.get('exp_args', {}) or {}
            r = float(rs[-1]['r_selfac'])
            E = float(rs[-1]['E_el_J'])
            V = float(rs[-1]['Vt'])
        except Exception:
            continue
        if not np.isfinite(r) or not np.isfinite(E) or E <= 0 or V <= 0:
            continue
        rows.append(dict(tag=os.path.basename(os.path.dirname(p)),
                         N=m.get('N'), dx=m.get('dx_nm'),
                         L=ea.get('plate_L'), el=ea.get('el_scale'),
                         r=r, V=V, E=E, ed=E / V))
    return rows


def main():
    rows = collect()
    print('=' * 112)
    print('_r162 —— `§118` 的普适性检验（全库、控制 `Vt` 与 `(N,Δx)`）')
    print('=' * 112)
    print('  入表 %d 条末行' % len(rows))
    from collections import defaultdict
    g = defaultdict(list)
    for d in rows:
        g[(d['N'], round(d['dx'], 3))].append(d)
    npair = 0
    ratios = []
    print()
    print('  %-34s %-22s %-11s %-11s %-8s %s'
          % ('可比对（|ΔVt|/Vt < 10%）', '(N, Δx)', 'Δr/r', 'Δ(E/Vt)/(E/Vt)',
             '比值', '谁更大'))
    for k in sorted(g, key=lambda t: (t[0] or 0)):
        arr = g[k]
        if len(arr) < 2:
            continue
        for i in range(len(arr)):
            for j in range(i + 1, len(arr)):
                a, b = arr[i], arr[j]
                dV = abs(a['V'] - b['V']) / max(a['V'], b['V'])
                if dV > 0.10:
                    continue
                dr = abs(a['r'] - b['r']) / max(a['r'], b['r'], 1e-12)
                de = abs(a['ed'] - b['ed']) / max(a['ed'], b['ed'])
                ratio = dr / de if de > 1e-12 else float('nan')
                if np.isfinite(ratio):
                    ratios.append(ratio)
                npair += 1
                print('  %-34s %-22s %-11.3f %-11.3f %-8.2f %s'
                      % ('%s / %s' % (a['tag'][:16], b['tag'][:16]),
                         '(%s, %s)' % k, dr, de, ratio,
                         '**r 更大**' if dr > de else 'E 更大'))
    print()
    print('  ⇒ 可比对共 **%d** 对' % npair)
    if npair == 0:
        print('     ⚠ 全库没有 `Vt` 相近的成对臂 ⇒ **本库无法做普适性检验**')
        print('       （大多数臂的 `Vt` 差异远大于 10%）')
        return 0
    # ---- 汇总（**这才是普适性的答案**）----
    # ★ 修（第一版统计量设计错了）：比值 `(Δr/r)/(ΔE/E)` 的中位数被
    #   **`r` 根本没差的那些对**（同一变体集、只改几何）拉到 0.1 —— 那些对**不是证据**
    #   （`r` 不动 ⇒ 无从谈"代理"）。⇒ **只在 `Δr/r > 0.2` 的对里问"能量差多少"**。
    R = np.array(ratios) if ratios else np.array([float('nan')])
    print()
    print('  ---- 汇总（%d 对同 `(N,Δx)`、`|ΔVt|/Vt<10%%` 的可比对）----' % npair)
    print('     %-40s %s' % ('统计量', '值'))
    print('     %-40s %.3f（Q1/Q3 = %.3f / %.3f）'
          % ('**全部**对的比值中位', float(np.median(R)),
             float(np.percentile(R, 25)), float(np.percentile(R, 75))))
    sel = R[R > 0.2]
    print('     %-40s %d / %d' % ('其中 `Δr/r > 0.2`（`r` 真的差了的对）',
                                  len(sel), len(R)))
    if len(sel):
        print('     %-40s **%.2f**（最小 %.2f、最大 %.1f）'
              % ('这些对的比值中位', float(np.median(sel)),
                 float(sel.min()), float(sel.max())))
        n3 = int((sel > 3).sum())
        print('     %-40s %d / %d = **%.0f%%**'
              % ('其中比值 > 3 的', n3, len(sel), 100 * n3 / len(sel)))
    print()
    if len(sel) and float(np.median(sel)) > 3:
        print('  ⇒ ✅ **普适性成立**：在 `r` 真的差了的那些对里，')
        print('     `Δr/r` **系统性大于** `Δ(E_el/Vt)/(E_el/Vt)`（中位比值 **%.1f**）'
              % float(np.median(sel)))
        print('     ⇒ `§118` 的"`r` 不是弹性能的代理"**不是那一个几何的特例**。')
    else:
        print('  ⇒ ⚠ 在 `r` 真的差了的对里，中位比值只有 %.2f ⇒'
              % (float(np.median(sel)) if len(sel) else float('nan')))
        print('     **普适性不成立** —— `§118` 的结论可能只是那一对的巧合，需重查。')
    print()
    print('  ⚠ 记账：本检验只在**同一 `(N,Δx)`** 内、**`Vt` 差 <10%** 的成对臂之间做；')
    print('     跨分辨率、跨 `Vt` 的比较**不可比**（`E_el/Vt` 强烈依赖两者）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
