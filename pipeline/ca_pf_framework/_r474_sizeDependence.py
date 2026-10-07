#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r474_sizeDependence.py —— ★★★★ **1B 的地基检验**：弹性自能密度依赖"尺寸"还是"形状"？

## 为什么这是 1B 成败的判据

准静态（1B）把"板条长到多大"交给**不动点**：

```
dG(t) = ΔG_v(T)  +  ed(t)  −  stk·κ(t)      （ed_0 ≡ 0 已验证）
```

要让这个方程给出**有限厚度**，必须有一项**随厚度 t 增长**。候选只有两个：
* `stk·κ(t)`：对薄板 `κ ≈ 2/t` ⇒ **随 t 减小** ⇒ **方向相反，不可能是它**；
* `ed(t)`：**它必须随 t 变**。

⚠ **而 Eshelby 的经典结论是：夹杂的弹性能密度在无限介质里与尺寸无关**（`ε⁰` 均匀
⇒ `σ` 均匀 ⇒ `E/V` 与尺寸无关）。若这条在**本模型 + 周期盒**里也成立，
那么 `ed` **与 t 无关**，不动点方程退化成：

```
dG = (ΔG_v + ed) − 2·stk/t
  · 若 (ΔG_v+ed) > 0 ⇒ 对**所有** t 都 dG > 0 ⇒ **无限长大**（直到碰撞）
  · 若 (ΔG_v+ed) < 0 ⇒ t 越大 dG 越负 ⇒ **溶解**
⇒ **只有"无限长"与"溶掉"两种结局，没有有限厚度。**
```

⇒ 那会直接影响成功判据 **C2（单根板条的三维几何量、长宽比符合物理）**：
**单根孤立板条在现有物理里可能根本没有确定的厚度。**

## 预登记判据（**先写死**）

用 `windowB_pf3d.PF3D`（其自检 6 条解析判据全过，`_r439` 已用过）。

| # | 检验 | 解析已知答案 | 判据 |
|---|---|---|---|
| **T1** | **球**，半径 `R ∈ {6,8,10,12,14}·Δx` | **尺寸无关**（Eshelby） | `max/min(E_el/V) ≤ 1.05` |
| **T2** | **板条，固定 L=1000/W=500 nm，扫厚度 t ∈ {125,187,250,375,510} nm** | **本题要问的** | 报 `max/min`；`≥1.20` ⇒ 厚度**显著**影响；`<1.05` ⇒ **无依赖** |
| **T3** | **自相似缩放**（L,W,t 同乘 `s ∈ {0.5,0.75,1.0,1.5,2.0}`） | **尺寸无关**（形状不变） | `max/min ≤ 1.05`（若不过 ⇒ T2 的依赖可能来自离散/周期像，不是形状） |
| **T4** | **负对照**：固定**体积**，球 → 扁球（`a=b=R0, c` 变） | **形状变化 ⇒ 能量密度必须大变** | `max/min ≥ 1.30`（**必须能失败**：若它不过，说明量具对形状不敏感，T2 不可信） |

⚠ 全部用**同一个变体**（7 号，`_r439` 里最优的那个），避免变体差异混淆；
`gamma=0`（纯弹性）。盒子 `N=96, L=6 µm` ⇒ 最大包含物 ~0.9 µm，离边界 ≥ 0.9 µm。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_pf3d as PF                                     # noqa: E402
from T16_verify_rve import C, EPS0                            # noqa: E402

DX = 62.5e-9
N = 96
VAR = 7                       # 用 7 号变体（`_r439` 实测最优）
TOL_SIZE = 1.05               # T1/T3：尺寸无关的容差
TOL_T2_STRONG = 1.20          # T2：厚度"显著影响"的门槛
TOL_T2_NONE = 1.05            # T2：厚度"无影响"的门槛
TOL_T4_MIN = 1.30             # T4：形状敏感的**下界**（必须能失败）


def P(s):
    print(s, flush=True)


def build():
    return PF.PF3D(N, DX * N, C, EPS0, gamma=0.0, w90=1.5 * DX, Lmob=1.0,
                   workers=1, k0_mode='free')


def ellipsoid_mask(g, radii):
    ii = (np.arange(g.N) + 0.5) * (g.L / g.N)
    X, Y, Z = np.meshgrid(ii - g.L / 2, ii - g.L / 2, ii - g.L / 2, indexing='ij')
    # ⚠ 记账：与 `_r439` 用**逐字相同**的构造（胞中心坐标），保证可比
    r = (X / radii[0]) ** 2 + (Y / radii[1]) ** 2 + (Z / radii[2]) ** 2
    return r <= 1.0


def energy_density(g, v, mask):
    """返回 (E_el, V_cells*dx³, E_el/V, ∫ε⁰:σ dV)。"""
    g.phi[:] = 0.0
    g.phi[v] = mask.astype(g.phi.dtype)
    E = float(g.E_el())
    sig = g.sigma_tensor()
    e0 = g.eps0_fields()
    Ied = float((e0 * sig).sum()) * g.dx ** 3
    V = mask.sum() * g.dx ** 3
    return E, V, (E / V if V > 0 else float('nan')), Ied


def sweep(g, v, family, label, tol, kind):
    """family: [(名字, radii), ...] ⇒ 报 E/V 的 max/min。"""
    P('\n[%s]' % label)
    P('     %-26s %-10s %-15s %-15s %s'
      % ('形状（半轴 nm）', '胞数', 'E_el (J)', 'E_el/V (J/m³)', 'E_el/(−½∫ε⁰:σ)'))
    dens, names = [], []
    for nm, radii in family:
        m = ellipsoid_mask(g, radii)
        E, V, d, Ied = energy_density(g, v, m)
        ratio = (E / (-0.5 * Ied)) if Ied != 0 else float('nan')
        dens.append(d); names.append(nm)
        P('     %-26s %-10d %-15.6e %-15.6e %.4f'
          % (nm, int(m.sum()), E, d, ratio))
    dens = np.array(dens)
    lo, hi = float(np.nanmin(dens)), float(np.nanmax(dens))
    ratio_mm = hi / lo if lo > 0 else float('nan')
    P('     ⇒ E_el/V 的 **max/min = %.4f**（min=%.4e  max=%.4e）' % (ratio_mm, lo, hi))
    if kind == 'const':
        ok = ratio_mm <= tol
        P('     ⇒ 判据（尺寸无关，≤ %.2f）：**%s**'
          % (tol, '✅ PASS' if ok else '❌ FAIL（有尺寸依赖 ⇒ 须查来源）'))
    elif kind == 'sensitive':
        ok = ratio_mm >= tol
        P('     ⇒ 判据（对形状必须敏感，≥ %.2f）：**%s**'
          % (tol, '✅ PASS（量具对形状敏感）' if ok
             else '❌ FAIL（量具对形状不敏感 ⇒ T2 不可信）'))
    else:
        ok = None
        P('     ⇒ 判据：≥%.2f ⇒ 厚度**显著**影响；<%.2f ⇒ **无依赖**（⇒ 1B 定不出有限厚度）'
          % (TOL_T2_STRONG, TOL_T2_NONE))
        if ratio_mm >= TOL_T2_STRONG:
            P('     ⇒ **判定：厚度显著影响弹性能密度 ⇒ 1B 有定尺寸机制** ✅')
        elif ratio_mm >= TOL_T2_NONE:
            P('     ⇒ **判定：弱依赖**（%.2f–%.2f 之间）⇒ 须再细分' % (TOL_T2_NONE, TOL_T2_STRONG))
        else:
            P('     ⇒ **判定：无依赖 ⇒ 单根孤立板条的弹性项定不出有限厚度** ⚠⚠')
    return ratio_mm, ok


def main():
    P('=' * 96)
    P('_r474  弹性自能密度：依赖"尺寸"还是"形状"？（1B 的地基检验）')
    P('  求解器 windowB_pf3d.PF3D   变体 %d   gamma=0   N=%d  L=%.1f µm  Δx=%.1f nm'
      % (VAR, N, N * DX * 1e6, DX * 1e9))
    P('=' * 96)
    g = build()
    v = VAR - 1

    # ---- T1 球：尺寸无关（正对照）----
    R = [6, 8, 10, 12, 14]
    r1, ok1 = sweep(g, v,
                    [('%ddx 球 (R=%.0f nm)' % (k, k * DX * 1e9), (k * DX,) * 3) for k in R],
                    'T1 球：尺寸无关（Eshelby 正对照）', TOL_SIZE, 'const')

    # ---- T3 自相似缩放：尺寸无关（形状不变）----
    base = (1000e-9 / 2, 500e-9 / 2, 510e-9 / 2)
    scales = [0.5, 0.75, 1.0, 1.5, 2.0]
    r3, ok3 = sweep(g, v,
                    [('自相似 ×%.2f (t=%.0f nm)' % (s, 510 * s),
                      tuple(x * s for x in base)) for s in scales],
                    'T3 板条自相似缩放：尺寸无关（形状不变）', TOL_SIZE, 'const')

    # ---- T2 固定 L/W、扫厚度（本题要问的）----
    ts = [125, 187.5, 250, 375, 510]
    r2, _ = sweep(g, v,
                  [('t=%.0f nm (t/Δx=%.1f)' % (t, t / (DX * 1e9)),
                    (1000e-9 / 2, 500e-9 / 2, t * 1e-9 / 2)) for t in ts],
                  'T2 板条：固定 L=1000/W=500，**扫厚度 t**', None, 'question')

    # ---- T4 负对照：固定体积，球 → 扁球（形状大变）----
    V0 = (4.0 / 3.0) * np.pi * (10 * DX) ** 3          # 以 10dx 球的体积为基准
    c_list = [10.0, 6.0, 4.0, 3.0, 2.0]                # c 减小 ⇒ 越扁（a=b 相应增大以保体积）
    fam = []
    for c in c_list:
        a = (V0 * 3.0 / (4.0 * np.pi * (c * DX))) ** 0.5
        fam.append(('扁球 a=b=%.0fnm c=%.0fnm' % (a * 1e9, c * DX * 1e9), (a, a, c * DX)))
    r4, ok4 = sweep(g, v, fam, 'T4 负对照：固定体积、球→扁球（形状必须敏感）',
                    TOL_T4_MIN, 'sensitive')

    # ---------------- 汇总 ----------------
    P('\n' + '=' * 96)
    P('★ 汇总')
    P('  T1 球尺寸无关      max/min = %.4f  %s' % (r1, 'PASS' if ok1 else 'FAIL'))
    P('  T3 自相似尺寸无关  max/min = %.4f  %s' % (r3, 'PASS' if ok3 else 'FAIL'))
    P('  T2 扫厚度          max/min = %.4f   ⇒ %s'
      % (r2, '厚度显著影响' if r2 >= TOL_T2_STRONG else
         ('弱依赖' if r2 >= TOL_T2_NONE else '**无依赖**')))
    P('  T4 形状敏感（负对照）max/min = %.4f  %s' % (r4, 'PASS' if ok4 else 'FAIL'))
    P('')
    if ok1 and ok3:
        P('  ⇒ 正/负对照通过 ⇒ **量具可信**：它在"形状不变"时给常数、在"形状变"时给出变化。')
    else:
        P('  ⇒ ⚠ **正或负对照没过 ⇒ 量具不可信，T2 的读数不得引用。**')
    if ok4 and ok1 and ok3:
        if r2 < TOL_T2_NONE:
            P('  ⇒ **结论：单一孤立板条的弹性能密度几乎不随厚度变** ⇒')
            P('     不动点方程 `dG = (ΔG_v+ed) − 2·stk/t` 只有"无限长大"或"溶掉"两种解，')
            P('     **没有有限厚度** ⇒ **C2（单根板条几何）在现有物理里缺一个定尺寸机制。**')
            P('     ⇒ 需要的是：①集体弹性（多根之间的 mean-field 应力）；②碰撞/充满；')
            P('        ③或补一个物理的界面拖曳项（但**不得自己编**，见 §改 3 的纪律）。')
        else:
            P('  ⇒ **结论：厚度确实影响弹性能密度（%.2f×）⇒ 1B 有定尺寸机制。**' % r2)
    P('=' * 96)
    return 0


if __name__ == '__main__':
    sys.exit(main())
