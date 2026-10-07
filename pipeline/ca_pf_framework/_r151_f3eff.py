#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r151_f3eff.py —— **F3 抹平窗口有没有物理后果？**（`§99` 明确留下的未办事项）

## `§99` 写了什么

> 「⚠ 尚未查：抹平窗口对**动力学**的影响（比如"块在这 100 步里是不是被当成了两根独立的板条"）」

## 本脚本怎么问

`dry_mb2fp10`（`--facet-proj 10`）与 `dry_mb2fp0`（`proj=0`）是**同一次运行的两条臂**，
种子逐位相同 ⇒ **只差投影**。而投影在 **step 20 把 `f3_area` 从 4.108 抹到恰好 0**，
~100 步后才恢复。

**⇒ 若 F3 界面（低角晶界）在动力学里真的起作用**，那么：
* **抹平窗口内（step 20–100）**：块内两根失去了 LAGB 约束 ⇒
  **转变速率或界面几何应当出现与对照臂的系统性差异**；
* **恢复之后（step ≥120）**：两臂的差异应当**收敛**（或转为投影带来的形状差异）。

## 报什么（**只用末行/全行，不截断数字**）

1. `ΔVt/Δstep`（每 20 步）在两臂上的**逐段**对照；
2. 抹平窗口（step ≤100）与恢复后（step ≥120）的**分段平均速率**；
3. `f3_area_m2` 与 `nf2` 的逐段值（把"抹平窗口"的边界**当场画出来**）。

⚠ **记账**：两臂除了"抹平 F3"之外，投影还会**把每个场重塑成盒子**
（改变界面面积/曲率）⇒ **差异不能全部归因于 F3**。本脚本只回答
"**有没有**可测的动力学差异、以及它出现在**哪个窗口**"，**不**做因果定量。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def load(tag):
    p = os.path.join(MB, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {}
    for key in ('step', 'Vt', 'f3_area_m2', 'nf2', 'nslab_n'):
        vals = []
        for r in rows:
            try:
                vals.append(float(r.get(key, 'nan') or 'nan'))
            except (TypeError, ValueError):
                vals.append(float('nan'))
        out[key] = np.array(vals)
    return out


def rate(a, lo, hi):
    """窗口 `[lo, hi]` 内的 `ΔVt/Δstep`（线性拟合斜率）。"""
    m = (a['step'] >= lo) & (a['step'] <= hi)
    if m.sum() < 2:
        return float('nan')
    return float(np.polyfit(a['step'][m], a['Vt'][m], 1)[0]) * 1e18  # µm³/步


def main():
    A = load('dry_mb2fp10')
    B = load('dry_mb2fp0')
    if A is None or B is None:
        print('⚠ 两臂数据不全')
        return 2
    print('=' * 108)
    print('_r151 —— F3 抹平窗口（step 20–100）有没有动力学后果？')
    print('=' * 108)
    print('  记账：两臂**只差 `--facet-proj`**（同一次 `_r75_mb.sh` 的两条臂），')
    print('        初值逐位相同 ⇒ 差异只能来自投影（但投影既抹 F3、又重塑盒子，**混在一起**）。')
    print()
    print('  %-7s %-13s %-13s %-11s %-13s %-13s %-11s %s'
          % ('step', 'proj=10 Vt', 'proj=0 Vt', 'ΔVt(µm³)', 'proj=10 f3',
             'proj=0 f3', 'nslab 10/0', 'nf2 10/0'))
    ks = sorted(set(A['step'].tolist()) & set(B['step'].tolist()))
    for k in ks:
        i = int(np.where(A['step'] == k)[0][0])
        j = int(np.where(B['step'] == k)[0][0])
        mark = '   ← **抹平窗口**' if 15 <= k <= 105 else ''
        # ⚠ `Vt` 在 CSV 里是 **m³** ⇒ 显示要 ×1e18（第一版忘了 ⇒ 全印成 0.0000）
        print('  %-7d %-13.4f %-13.4f %+-11.5f %-13.5f %-13.5f %-11s %d/%d%s'
              % (k, A['Vt'][i] * 1e18, B['Vt'][j] * 1e18,
                 (A['Vt'][i] - B['Vt'][j]) * 1e18,
                 A['f3_area_m2'][i] * 1e12, B['f3_area_m2'][j] * 1e12,
                 '%d/%d' % (A['nslab_n'][i], B['nslab_n'][j]),
                 int(A['nf2'][i]), int(B['nf2'][j]), mark))
    print()
    print('  ---- 分段速率 `ΔVt/Δstep`（µm³/步，`§84` 规程③：`Vt` 是**广延量**，只作速率用）----')
    print('  %-26s %-16s %-16s %s' % ('窗口', 'proj=10', 'proj=0', '差'))
    for lab, lo, hi in (('抹平窗口 0–100', 0, 100),
                        ('恢复后 120–300', 120, 300),
                        ('末段 400–600', 400, 600),
                        ('全程 0–600', 0, 600)):
        ra, rb = rate(A, lo, hi), rate(B, lo, hi)
        print('  %-26s %-16.6f %-16.6f %+.6f（%+.1f%%）'
              % (lab, ra, rb, ra - rb,
                 100 * (ra / rb - 1) if rb else float('nan')))
    print()
    print('  ---- 判读 ----')
    ra, rb = rate(A, 0, 100), rate(B, 0, 100)
    rc, rd = rate(A, 120, 300), rate(B, 120, 300)
    d1 = ra / rb - 1 if rb else float('nan')
    d2 = rc / rd - 1 if rd else float('nan')
    print('     抹平窗口内相对差 = **%+.1f%%**；恢复后相对差 = **%+.1f%%**' % (100 * d1, 100 * d2))
    if abs(d1) > 0.05 and abs(d1) > abs(d2):
        print('     ⇒ ⚠ **抹平窗口内的差异比恢复后更大** ⇒ 与"F3 约束在窗口内缺失"**一致**')
        print('        （⚠ 但投影同时重塑了盒子 ⇒ 不能单独归因给 F3，见文件头记账）')
    elif abs(d1) < 0.02:
        print('     ⇒ 抹平窗口内的速率**几乎没差**（<2%）⇒')
        print('        在这个量上看**不到** F3 抹平的动力学后果（**不等于没有**，只说明这个量不敏感）')
    else:
        print('     ⇒ 差异模式与"F3 缺失"不完全一致 ⇒ 需另设观测量')
    return 0


if __name__ == '__main__':
    sys.exit(main())
