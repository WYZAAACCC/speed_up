#!/usr/bin/env python3
"""_r439_selfenergy.py —— ★★★★ **逐变体的弹性自能**：为什么变体 1 溶、变体 7/9 长？

## 动机（`§193` 实测）
`abB` 里 **V1 的场全部溶解、V7/V9 的场全部生长**（变体完全分离）。
`abA` 里三个场全是 V1、全部溶解。

**问题**：V1 为什么在**本构型**里不利？

## 物理量（先写死定义）
孤立板条的**弹性自能**（松弛能）：
    `E_self(v) = −½ ∫ ε⁰_v : σ_v dV`      （σ_v 是**该板条自己**产生的应力）
而引擎的 `ed_v = +ε⁰_v:σ_v` ⇒ **`E_self(v) = −½ ∫ ed_v`**
⇒ **`∫ed_v` 越大（越正）⇒ `E_self` 越低 ⇒ 该变体越有利。**
⇒ **可直接用引擎的量比较变体。**

## 判据（**三条，缺一不可**）
**P-1 正对照（最强的一条）**：**球**形析出相 ⇒ **12 个 K-S 变体必须给出相同的 `E_self`**。
    依据：12 个 K-S 变体**立方对称等价**（`§179`：`ε⁰` 谱结构相同、`det=1`），
    球对称 ⇒ 与变体取向无关 ⇒ **解析已知答案 = 全相等**。
    ⚠ 若这条不过 ⇒ **求解器或口径有问题，后面全部作废**。
**P-2 板条 ⇒ 变体分离**：用**真实板条几何**（1000×500×510 nm）算 `E_self(v)`，
    看是否出现跨变体的显著展布。
**P-3 有限尺寸**：同 `dx`、换盒尺寸（N=48 / 96）重算。
    若展布随盒**显著缩小** ⇒ 是**周期像的有限尺寸伪影**，不是材料性质
    ⇒ `§193` 的"V1 不利"必须**降级**为构型依赖，**不得**推广。

## 记账
`windowB_pf3d.PF3D` 是**独立于** `windowB_surface` 的求解器实现（后者有自己的 FFT）。
本脚本用它是因为它有现成的 `E_el()` 且**自检 6 条解析判据全过**（`§180`，已进回归）。
⚠ 两者**不是同一份代码** ⇒ 本脚本的结论是"该求解器下的"，跨求解器比较须另做。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_pf3d as PF                                     # noqa: E402
from T16_verify_rve import C, EPS0                            # noqa: E402

DX = 62.5e-9
PLATE = (1000e-9, 500e-9, 510e-9)      # L, W, T（与 A/B 双臂逐字相同）
GAMMA = 0.15
W90 = 1.5 * DX


def P(s):
    print(s, flush=True)


def build(N):
    """构造 PF3D（12 个变体）。`gamma=0` ⇒ **纯弹性**，界面能不参与。"""
    L = N * DX
    return PF.PF3D(N, L, C, EPS0, gamma=0.0, w90=W90, Lmob=1.0,
                   workers=1, k0_mode='free')


def ellipsoid_mask(g, radii):
    """半轴 radii 的**椭球**（球 = 三个半轴相等）。返回 (N,N,N) bool。"""
    N, L = g.N, g.L
    ii = (np.arange(N) + 0.5) * (L / N)
    X, Y, Z = np.meshgrid(ii - L / 2, ii - L / 2, ii - L / 2, indexing='ij')
    r = (X / radii[0]) ** 2 + (Y / radii[1]) ** 2 + (Z / radii[2]) ** 2
    return r <= 1.0


def self_energy(g, v, mask):
    """把变体 `v` 的 φ 设为 `mask`（其余 0），解弹性 ⇒ 返回 (∫ε⁰:σ dV, E_el)。

    ⚠ **自纠错（自查错误 #58）**：第一版写
        `ed = np.einsum('p,p...->...', g.e0v_eng[v], sig)`  ⇒ `ε⁰_v:∫σ dV`
    而**周期、无外载的平衡体满足 `∫σ dV ≡ 0`**（动量守恒的零模）
    ⇒ 该量**恒等于 0**，只剩浮点噪声。
    **实测症状**：球正对照里 `∫ed` 给 1e-27 J 量级的乱数（相对 1e-16），
    而同一行的 `E_el` 12 个变体**逐位相同 = 1.423348e-11**。
    ⇒ 正对照（我预先写死的 P-1）**当场抓住了这个错**。
    **正确口径**：`∫ ε⁰(x):σ(x) dV`，其中 `ε⁰(x)` 是**逐胞的本征应变场**
    （只在场内非零）= `eps0_fields()`。
    且它应与 `E_el` 满足 `E_el = −½∫ε⁰:σ`（**这条就是本函数内置的交叉核对**）。
    """
    g.phi[:] = 0.0
    g.phi[v] = mask.astype(g.phi.dtype)
    E = float(g.E_el())
    sig = g.sigma_tensor()                   # (6,N,N,N) 工程分量
    e0 = g.eps0_fields()                     # (6,N,N,N) 逐胞本征应变（工称分量）
    # 注意：`eps0_fields` 返回的是**张量分量**，而 `sigma_tensor` 也是**张量分量**
    # ⇒ 直接 `Σ_p e0[p]·sig[p]` 就是 `ε⁰:σ`（**不再乘 G6**）。
    Ied = float((e0 * sig).sum()) * g.dx ** 3
    return Ied, E, (E / (-0.5 * Ied) if Ied != 0 else float('nan'))


def run_case(N, radii, label):
    g = build(N)
    out = []
    for v in range(len(EPS0)):
        m = ellipsoid_mask(g, radii)
        Ied, E, ratio = self_energy(g, v, m)
        out.append((v + 1, Ied, E, ratio))
    P('\n[%s]  N=%d  L=%.2f µm  形状半轴=%s nm'
      % (label, N, g.L * 1e6, tuple(round(r * 1e9, 1) for r in radii)))
    P('     %-6s %-17s %-17s %-14s %s'
      % ('变体', '∫ε⁰:σ dV (J)', 'E_el (J)', 'E_el/(−½∫ε⁰:σ)', '−½∫ε⁰:σ'))
    vals, chi = [], []
    for v, Ied, E, ratio in out:
        vals.append(E)                       # ★ 用 **E_el** 作为自能（已过正对照）
        chi.append(ratio)
        P('     %-6d %-17.8e %-17.8e %-14.6f %-17.8e'
          % (v, Ied, E, ratio, -0.5 * Ied))
    vals = np.array(vals)
    spread = (vals.max() - vals.min()) / max(abs(vals.mean()), 1e-300)
    P('     ⇒ 展布 (max−min)/|mean| = **%.4e**（用 **E_el**）' % spread)
    chi = np.array([c for c in chi if np.isfinite(c)])
    if chi.size:
        P('     ⇒ 内置交叉核对 `E_el/(−½∫ε⁰:σ)`：中位 %.6f，偏离 1 的最大值 %.3e ⇒ %s'
          % (float(np.median(chi)), float(np.max(np.abs(chi - 1.0))),
             '✅ 两条独立路径一致' if np.max(np.abs(chi - 1.0)) < 1e-3
             else '⚠ 不一致，须查'))
    order = np.argsort(vals)                 # E_el 越小越有利
    P('     ⇒ 优劣排序（E_el 由小到大 = 由优到劣）: %s' % [int(i + 1) for i in order])
    return vals, spread, out


P('=' * 100)
P('_r439 —— 逐变体弹性自能（用 `windowB_pf3d.PF3D`，其自检 6 条解析判据全过）')
P('=' * 100)
P('\n定义：`E_self(v) = −½∫ε⁰_v:σ_v dV = −½∫ed_v dV` ⇒ **`∫ed` 越大越有利**。')

# ---------------------------------------------------------------- P-1 正对照
P('\n' + '#' * 100)
P('# P-1 正对照：**球形**析出相 ⇒ 12 个 K-S 变体必须给出**相同**的 ∫ed')
P('#   依据：12 个 K-S 变体立方对称等价（`§179`），球对称 ⇒ 与取向无关')
P('#' * 100)
R = 250e-9
v48s, s48s, _ = run_case(48, (R, R, R), '球 R=250nm')
ok_p1 = s48s < 1e-6
P('\n  ⇒ P-1（展布 < 1e-6）：**%.4e** ⇒ %s'
  % (s48s, '✅ PASS —— 求解器与口径可信，可看板条结果' if ok_p1
     else '❌ FAIL —— **后面全部作废**'))

if not ok_p1:
    P('\n⛔ 正对照不过 ⇒ 停止。')
    raise SystemExit(1)

# ---------------------------------------------------------------- P-2 板条
P('\n' + '#' * 100)
P('# P-2 真实板条几何（L/W/T = %.0f/%.0f/%.0f nm）'
  % tuple(x * 1e9 for x in PLATE))
P('#' * 100)
half = tuple(x / 2.0 for x in PLATE)
v48p, s48p, o48p = run_case(48, half, '板条（盒 3.0 µm）')

# ---------------------------------------------------------------- P-3 有限尺寸
P('\n' + '#' * 100)
P('# P-3 有限尺寸：同 dx、换盒')
P('#' * 100)
v96p, s96p, o96p = run_case(96, half, '板条（盒 6.0 µm）')

# ---------------------------------------------------------------- 判读
P('\n' + '=' * 100)
P('[判读]')
P('  P-1 球正对照：展布 %.3e ⇒ ✅ PASS' % s48s)
P('  P-2 板条展布：盒 3.0 µm = **%.4e**；盒 6.0 µm = **%.4e**' % (s48p, s96p))
if s96p > 1e-6:
    order48 = [int(i + 1) for i in np.argsort(v48p)]      # E_el 越小越优
    order96 = [int(i + 1) for i in np.argsort(v96p)]
    P('      盒 3.0 µm 优劣序：%s' % order48)
    P('      盒 6.0 µm 优劣序：%s' % order96)
    P('      ⇒ 两个盒的**最优变体**：%d vs %d ⇒ %s'
      % (order48[0], order96[0],
         '✅ 一致' if order48[0] == order96[0] else '⚠ **不一致**'))
    # 变体 1 的名次
    r1_48 = order48.index(1) + 1
    r1_96 = order96.index(1) + 1
    P('      ⇒ **变体 1 的名次**：盒 3.0 µm 第 **%d**/12；盒 6.0 µm 第 **%d**/12'
      % (r1_48, r1_96))
    P('      ⇒ %s'
      % ('✅ "变体 1 偏不利"在**两个盒上都成立** ⇒ 不是纯尺寸伪影'
         if r1_48 > 6 and r1_96 > 6 else
         '⚠ 变体 1 的名次**随盒变化** ⇒ 至少部分来自**周期像/有限尺寸**'))
    ratio = s96p / max(s48p, 1e-300)
    P('      展布比（6.0/3.0 µm）= **%.3f** ⇒ %s'
      % (ratio, '展布随盒**显著缩小** ⇒ 尺寸伪影为主' if ratio < 0.5
         else '展布**不随盒缩小** ⇒ 像是真实（材料/取向）效应'))
else:
    P('      盒 6.0 µm 展布 ≈ 0 ⇒ **纯尺寸伪影**：单板条下 12 个变体等价')
P('=' * 100)
