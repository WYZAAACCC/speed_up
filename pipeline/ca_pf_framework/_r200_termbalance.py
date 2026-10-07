#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r200_termbalance.py —— ★ `dG = df + Δed − stk·κ` 的**三项量级对比**（解释 R165 的否定结果）。

## 假设（**【推理】**，本脚本用量级检验它）

R165 的否定结果很奇怪：F2 的 γ 降了 **9.3×**、F2 界面占变体界面的 **74.5%**，
可 `r_selfac` 只动了 **0.03%**。若界面能项真的有话语权，这不合理。
**⇒ 猜测：`stk·κ` 项相对 `ed` 太小 ⇒ 界面能**根本没在**参与变体选择的角逐。**

## 怎么量（只用已有的日志列，不重跑）

速度律（`windowB_surface.py:3346`）：`dG = (df_k−df_l) + (ed_k−ed_l) − stk·κ`
* `df` 是**所有变体同值**的常数（`_bk_exp.py:586`）⇒ `df_k−df_l = 0`
* `ed_*` 列（`ed_tip`/`ed_side`/`ed_wide`）单位 **J/m³**
* `stk ≈ γ`（J/m²），`κ` 单位 **1/m** ⇒ `stk·κ` 也是 **J/m³**
* **κ 的网格上限**：中心差分下 `κ_max ~ 1/Δx`（再大就欠解析）
  ⇒ `(stk·κ)_max ≈ γ/Δx`

⇒ 比较 `γ/Δx` 与 `|ed|` 的量级。若差 1~2 个数量级 ⇒ 界面能项**结构性**弱势。
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARMS = ('saSet2', 'saSet2F2', 'saOddG', 'saOddGF2', 'mb2fp10')


def main():
    print('=' * 104)
    print('_r200 —— `dG = df + Δed − stk·κ` 三项量级对比')
    print('=' * 104)
    print()
    for arm in ARMS:
        d = os.path.join(MB, 'dry_' + arm)
        mp = os.path.join(d, 'meta.json')
        cp = os.path.join(d, 'series.csv')
        if not (os.path.exists(mp) and os.path.exists(cp)):
            print('  %-12s (缺数据)' % arm)
            continue
        m = json.load(open(mp))
        g0 = float(m.get('gamma0', 0.25))
        dx = float(m.get('dx_nm', 62.5)) * 1e-9
        # athermal 的 df 随 T 变；这里取 meta 能给的
        dfc = m.get('df_const')
        dfs = m.get('df_start')
        with io.open(cp, 'r', encoding='utf-8') as f:
            rs = list(csv.DictReader(f))
        last = rs[-1]

        def g(k):
            try:
                return float(last.get(k, 'nan'))
            except (TypeError, ValueError):
                return float('nan')

        eds = [g('ed_tip'), g('ed_side'), g('ed_wide'), g('ed_obl')]
        eds = [abs(x) for x in eds if np.isfinite(x)]
        ed_typ = float(np.median(eds)) if eds else float('nan')
        # F3 的 γ（同变体低角）—— 用 ladder(5°) M=12 的实测值
        gF3 = 0.053972
        kappa_max = 1.0 / dx                      # 网格上限
        stk_kappa_max = g0 * kappa_max            # F2 用标量 γ₀
        stk_kappa_max3 = gF3 * kappa_max          # F3 用低角 γ
        dGmax = g('dG_max_Jm3')
        print('  ## `%s`' % arm)
        print('     γ₀=%.3f J/m²  γ_F3=%.4f J/m²  Δx=%.1f nm  '
              'df_const=%s  df_start=%s' % (g0, gF3, dx * 1e9, dfc, dfs))
        print('     `ed_*` 典型量级（中位）        = **%.3e J/m³**' % ed_typ)
        print('     `stk·κ` 上限（κ_max=1/Δx, F2 用 γ₀）= **%.3e J/m³**'
              % stk_kappa_max)
        print('     `stk·κ` 上限（F3 用 γ_F3）        = **%.3e J/m³**' % stk_kappa_max3)
        print('     `dG_max_Jm3`（实测）              = **%.3e J/m³**' % dGmax)
        if np.isfinite(ed_typ) and ed_typ > 0:
            r1 = stk_kappa_max / ed_typ
            r3 = stk_kappa_max3 / ed_typ
            print('     ⇒ **|stk·κ|_max / |ed| = %.3e（F2）/ %.3e（F3）**' % (r1, r3))
            print('     ⇒ ⇒ 界面能项至多是弹性项的 **%.2f%%**（F2）/ **%.2f%%**（F3）'
                  % (100 * r1, 100 * r3))
        print()
    print('=' * 104)
    print('  ## 解读')
    print('=' * 104)
    print('     · `κ` 的真实值还受**界面形状**限制：板条厚 ~500 nm ⇒ κ ~ 1/250nm = 4e6 /m')
    print('       ⇒ `stk·κ ~ 0.25 × 4e6 = 1e6 J/m³`，比 `|ed| ~ 4e8` **小 400 倍**。')
    print('     · **⇒ 界面能项（含 F2 配对 γ、F3 的 γ_RS、`ncmp` 的取向择优）')
    print('       在速度律里是**结构性弱势**的，改它不会改变变体选择。**')
    print('     · ⇒ 与 R165 的**否定结果完全一致**，也解释了 `§132.5` 为何量不到 `ncmp` 择优。')
    print()
    print('  ⚠ **本条是【推理】**（量级估计，未逐胞求 κ 后积分）。')
    print('     决定性检验：在 `advance` 里**逐胞记录** `|df|`、`|Δed|`、`|stk·κ|` 三项的')
    print('     分布（新增诊断列），直接看 `stk·κ` 的占比 —— **本轮未做**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
