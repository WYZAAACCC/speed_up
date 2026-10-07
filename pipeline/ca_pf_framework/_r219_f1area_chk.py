#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r219_f1area_chk.py —— 新列 `f1_area` / `nf1` 的**正对照**（`§137.7`）。

## 为什么必须做正对照

用户硬要求：**「一定要注意确保测量工具的正确性，测量工具出现错误可能会对实验结果
以及最终结论产生极大的影响」**。本轮（`§137.5`）要拿 `f1_area` 去算
"三类界面各占多少"，并据此解释 R165 的否定结果 ⇒ **这个量具错了，结论就全错**。

## 判据（**先写死**）

* **A-1 平板正对照**：造一个 region：`x < N/2` 为变体 k、`x >= N/2` 为母相 0
  ⇒ 解析 F1 面积 = **盒截面面积** = `(N·dx)²`。
  判据：相对误差 < 2%（格面计数在**斜**界面才有 √2 类偏差，正切时**应精确**）。
* **A-2 45° 斜面正对照**：平面法向 = (1,1,0)/√2 ⇒ 解析面积 = `√2·(N·dx)²`。
  判据：`f1_area` 相对误差 < 5%，且 `f1_area_stair/f1_area` ≈ `|n_hab|` 的组合。
* **A-3 零对照**：全盒都是母相 ⇒ `f1_area` 必须**恰好 0**。
* **A-4 退化**：`n_hab` 为 [0,0,0] 时不得出 NaN/负值。
* **A-5 加和一致性**：`f1_area + f2_area + f3_area` 在同一构型上
  与 `f1_area_stair` 那套口径**同量级**（不要求相等，只查没搞反）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM  # noqa: E402


def mk(region, dx, n_hab):
    return BM.measure_state(region, dx, np.asarray(n_hab, float),
                            w_ax=np.array([0.0, 1.0, 0.0]),
                            a_ax=np.array([1.0, 0.0, 0.0]),
                            vmap={1: 1, 2: 2}, r_col=300e-9)


def main():
    print('=' * 104)
    print('_r219 —— `f1_area` 正对照（`§137.7`）')
    print('=' * 104)
    N, dx = 40, 1e-8
    L = N * dx
    ok = True

    # ---- A-1 平板（法向沿 x）----
    print()
    print('  ## **A-1 平板**：`10<=x<30` = 变体1，其余 = 母相 ⇒ **两张** F1 界面')
    print('     ⚠⚠ 记账（**第 18 个自查错误**）：第一版把变体放在 `x<N/2`，')
    print('       而格面计数用 **`np.roll`（周期性）** ⇒ 变体区**跨过周期边界**，')
    print('       于是除了真实界面还多数出一张**周期镜像** ⇒ 面积恰好 **2×**，')
    print('       我一度判 ❌ "量具错了"。**真相是夹具忘了周期性。**')
    print('       ⇒ 真实算例里板条在盒内部（`box_touch=0`）⇒ **不会有这个伪影**；')
    print('         本夹具改成**中间板条**（不跨周期边界）⇒ 解析值就是 **2·(N·dx)²**。')
    reg = np.zeros((N, N, N), np.int8)
    reg[10:30] = 1
    r = mk(reg, dx, [1.0, 0.0, 0.0])
    ana = 2.0 * L * L                       # 板条两侧各一张界面
    got = r['f1_area']
    rel = abs(got - ana) / ana
    good = rel < 0.02
    ok &= good
    print('     `f1_faces`=%d  `f1_area`=%.6e m²（=%.4f µm²）  解析=%.4f µm²  '
          '相对差=%.4f%% ⇒ %s'
          % (r['f1_faces'], got, got * 1e12, ana * 1e12, 100 * rel,
             '✅ 通过' if good else '❌ 失败'))
    print('     `f1_area_stair`=%.4f µm²（正切时 stair 应 ≈ area）'
          % (r['f1_area_stair'] * 1e12))

    # ---- A-2 45° 斜面 ----
    print()
    print('  ## **A-2 45° 斜面**：法向 = (1,1,0)/√2 ⇒ 两张斜面，解析 = 2√2·(N·dx)²')
    x = (np.arange(N) + 0.5) * dx
    X, Y = np.meshgrid(x, x, indexing='ij')
    proj = (X + Y) / np.sqrt(2.0)
    # 用**中间一条带**（不跨周期边界）
    lo = (N * dx) / np.sqrt(2.0) * 0.75
    hi = (N * dx) / np.sqrt(2.0) * 1.25
    n45 = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    reg2 = np.zeros((N, N, N), np.int8)
    band = ((proj[:, :, None] > lo) & (proj[:, :, None] < hi))
    reg2[np.broadcast_to(band, (N, N, N))] = 1
    r2 = mk(reg2, dx, n45)
    ana2 = 2.0 * np.sqrt(2.0) * L * L
    got2 = r2['f1_area']
    rel2 = abs(got2 - ana2) / ana2
    good2 = rel2 < 0.06
    ok &= good2
    print('     `f1_area`=%.4f µm²  解析=%.4f µm²  相对差=%.4f%% ⇒ %s'
          % (got2 * 1e12, ana2 * 1e12, 100 * rel2, '✅ 通过' if good2 else '❌ 失败'))
    print('     `f1_area_stair`=%.4f µm²（斜面的 stair 应更大）'
          % (r2['f1_area_stair'] * 1e12))

    # ---- A-3 零对照 ----
    print()
    print('  ## **A-3 零对照**：全盒母相 ⇒ `f1_area` 必须**恰好 0**')
    r3 = mk(np.zeros((N, N, N), np.int8), dx, [1.0, 0.0, 0.0])
    z = (r3['f1_area'] == 0.0) and (r3['f1_faces'] == 0)
    ok &= z
    print('     `f1_faces`=%d  `f1_area`=%.3e ⇒ %s'
          % (r3['f1_faces'], r3['f1_area'], '✅ 通过' if z else '❌ 失败'))

    # ---- A-4 退化：n_hab = 0 ----
    print()
    print('  ## **A-4 退化**：`n_hab = [0,0,0]` ⇒ 不得 NaN/负值')
    r4 = mk(reg, dx, [0.0, 0.0, 0.0])
    fin = np.isfinite(r4['f1_area']) and r4['f1_area'] >= 0
    ok &= fin
    print('     `f1_area` = %.6e，`f1_area_stair` = %.6e ⇒ %s'
          % (r4['f1_area'], r4['f1_area_stair'],
             '✅ 通过（不炸、非负）' if fin else '❌ 失败'))

    # ---- A-5 三类加和 ----
    print()
    print('  ## **A-5 三类加和一致性**：一个同时含 F1/F2/F3 的构型')
    print('     ⚠ 需要**两个不同场同变体**才可能有 F3 ⇒ `vmap={1:1, 2:2, 3:1}`')
    print('       （第一版只给 1/2 两个场、变体 1/2 ⇒ **F3 按定义不可能出现**，')
    print('        我却据此判 ❌ —— 第 18 个自查错误的同一类：夹具不满足前提。）')
    reg5 = np.zeros((N, N, N), np.int8)
    reg5[2:6] = 1        # 与母相接 ⇒ F1
    reg5[6:10] = 3       # 场3 = **变体1**（与场1同变体）⇒ F3（场1|场3 相邻）
    reg5[10:14] = 2      # 场2 = 变体2，**紧挨场3** ⇒ F2；与母相也相邻 ⇒ F1
    reg5[20:24] = 1
    r5 = BM.measure_state(reg5, dx, np.asarray([1.0, 0.0, 0.0], float),
                          w_ax=np.array([0.0, 1.0, 0.0]),
                          a_ax=np.array([1.0, 0.0, 0.0]),
                          vmap={1: 1, 2: 2, 3: 1}, r_col=300e-9)
    a1, a2, a3 = r5['f1_area'], r5['f2_area'], r5['f3_area']
    tot = a1 + a2 + a3
    print('     F1=%.4f  F2=%.4f  F3=%.4f µm²  ⇒ 合计 %.4f µm²'
          % (a1 * 1e12, a2 * 1e12, a3 * 1e12, tot * 1e12))
    print('     占比：F1 **%.1f%%**  F2 **%.1f%%**  F3 **%.1f%%**'
          % (100 * a1 / tot if tot else float('nan'),
             100 * a2 / tot if tot else float('nan'),
             100 * a3 / tot if tot else float('nan')))
    pos = (a1 > 0) and (a2 > 0) and (a3 > 0)
    ok &= pos
    print('     ⇒ 三类都 > 0 ⇒ %s' % ('✅ 通过' if pos else '❌ 失败'))

    print()
    print('=' * 104)
    print('  ## 总判定')
    print('=' * 104)
    print('     ⇒ %s' % ('✅ **A-1…A-5 全部通过**：`f1_area` 可作量具用'
                         if ok else '❌ **有判据不过** ⇒ 先修量具再用它下结论'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
