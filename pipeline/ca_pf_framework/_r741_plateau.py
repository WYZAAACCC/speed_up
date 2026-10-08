#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r741_plateau.py —— 给 `big700` 的 `f2_area(t)` 拟**平台模型**，报渐近值。

## 为什么
`R741 §5.1` 的 9 个测点显示：`f2_area` 单调上升（5.174 → 7.361 µm²），
但**每 50 步的相对增长在单调下降**（13.1% → 10.7% → 7.7% → 5.5%）
⇒ 看起来趋于平台。**"趋于平台"不能只靠眼看** ⇒ 拟一个模型并报渐近值与拟合优度。

## 模型（两个，都报 —— 避免单选模型的偏袒）
| 模型 | 形式 | 渐近值 |
|---|---|---|
| **M1 扩散型** | `A(t) = A∞ − B·t^(−1/2)` | `A∞` |
| **M2 指数型** | `A(t) = A∞ − B·exp(−t/τ)` | `A∞` |

## 判据（**先登记**）
* **P-1**：两个模型的 `A∞` 相差 **< 10%** ⇒ 平台值**对模型选择稳健**；
* **P-2**：拟合 `R² > 0.99` ⇒ 模型形式合适；
* 否则**只报"仍在增长"**，不给渐近值。
"""
import csv
import os
import sys

import numpy as np

ROOT = '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_t2big/dry_big700'


def main():
    p = os.path.join(ROOT, 'series.csv')
    with open(p, newline='') as f:
        rows = [r for r in csv.DictReader(f) if r.get('step')]
    t = np.array([float(r['step']) for r in rows])
    a = np.array([float(r['f2_area_m2']) for r in rows])
    # ⚠⚠ **量具更正（2026-10-08，本次实测抓出）**：
    #   列名是 `f2_area_m2`（**m²**），而我第一版把公式里的单位写成 **µm²** 并按
    #   `%.6f` 打印 ⇒ 真实值 ~5e-12 m² 被截成 **0.000000** ⇒ 拟合给出
    #   `A∞ = 0.000000`、`R²(M1) = 0.361` ⇒ **全是假读数**。
    #   ⇒ 正解：**先换算成 µm²**（`× 1e12`）再拟合/打印。
    a = a * 1e12
    nf = np.array([float(r['nf2']) for r in rows])
    print('=' * 96)
    print('`big700` 的 `f2_area(t)` 平台模型（%d 个测点，step %g–%g）'
          % (len(t), t[0], t[-1]))
    print('  ⚠ 源列 `f2_area_m2` 单位是 **m²**；本脚本已 `×1e12` 换算成 **µm²**')
    print('=' * 96)
    print('  %-8s %14s %14s %12s' % ('step', 'nf2', 'f2_area_m2', '区间Δ'))
    prev = None
    for i in range(len(t)):
        d = '' if prev is None else '%+.4f' % (a[i] - prev)
        print('  %-8g %14.0f %14.6f %12s' % (t[i], nf[i], a[i], d))
        prev = a[i]
    print()

    tt = t.copy()
    tt[tt == 0] = 1e-9          # 避免 t=0 的奇点

    # M1: A = Ainf - B * t^(-1/2)   线性化：A = Ainf - B * u, u = t^(-1/2)
    u = tt ** -0.5
    c1 = np.polyfit(u, a, 1)
    Ainf1, B1 = c1[1], -c1[0]
    pred1 = Ainf1 + c1[0] * u
    r2_1 = 1 - ((a - pred1) ** 2).sum() / ((a - a.mean()) ** 2).sum()
    print('  **M1 扩散型** `A = A∞ − B·t^(−1/2)`')
    print('     A∞ = %.6f µm²   B = %.6f   R² = %.6f' % (Ainf1, B1, r2_1))

    # M2: A = Ainf - B*exp(-t/tau)   非线性（网格搜 tau + 线性解 B, Ainf）
    best = None
    for tau in np.linspace(20.0, 2000.0, 4000):
        e = np.exp(-tt / tau)
        c = np.polyfit(e, a, 1)
        pred = c[0] * e + c[1]
        r2 = 1 - ((a - pred) ** 2).sum() / ((a - a.mean()) ** 2).sum()
        if best is None or r2 > best[0]:
            best = (r2, tau, c[0], c[1])
    r2_2, tau2, B2, Ainf2 = best
    print('  **M2 指数型** `A = A∞ − B·exp(−t/τ)`')
    print('     A∞ = %.6f µm²   B = %.6f   τ = %.1f 步   R² = %.6f'
          % (Ainf2, -B2, tau2, r2_2))
    print()
    rel = abs(Ainf1 - Ainf2) / max(abs(Ainf2), 1e-30)
    print('  ## 判定')
    print('     P-1 两模型 A∞ 相对差 = %.4f%% ⇒ %s'
          % (100 * rel, '✅ <10% 稳健' if rel < 0.10 else '⛔ >10% 不稳健'))
    print('     P-2 拟合 R²：M1 = %.6f，M2 = %.6f ⇒ %s'
          % (r2_1, r2_2,
             '✅ 均 >0.99' if min(r2_1, r2_2) > 0.99 else '⛔ 有 <0.99'))
    print()
    if rel < 0.10 and min(r2_1, r2_2) > 0.99:
        print('  ⇒ ⇒ **`f2_area` 趋于平台 ≈ %.3f µm²**（当前 %.3f，已走完 %.1f%%）'
              % ((Ainf1 + Ainf2) / 2, a[-1], 100 * a[-1] / ((Ainf1 + Ainf2) / 2)))
    else:
        print('  ⇒ ⚪ 模型不稳或拟合不佳 ⇒ **只报"仍在增长"**，不给渐近值')
    print()
    print('  ⚠ 记账：`box_touch = 1`（板条触盒）⇒ 平台**可能部分来自盒的几何限制**，')
    print('     不全是物理饱和 ⇒ 本平台值**不可当作材料常数**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
