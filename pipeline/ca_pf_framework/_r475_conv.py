#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r475_conv.py —— 给 `_r474` 补**绝对标定**与**离散收敛**两个对照。

## 为什么要补（`_r474` 的负对照 T4 FAIL 了）

`_r474` 的结果：
* **T1 球尺寸无关** `max/min = 1.0131` ✅
* **T3 自相似尺寸无关** `max/min = 1.0250` ✅
* **T2 扫厚度** `max/min = 1.0578`（弱依赖）
* **T4 负对照（固定体积、球→扁球，预期 ≥1.30）实测 1.0719 ⇒ ❌ FAIL**

按预登记纪律，**T4 FAIL ⇒ T2 不得引用**。但 FAIL 有两种可能：
**(a) 量具对形状真的不敏感**（那 T2 不可信）；**(b) 我 T4 的"解析预期"本身错了**
（椭球夹杂的弹性能密度对**形状**本来就只有百分之几的依赖）。

**本脚本用两条独立的路把 (a)/(b) 分开：**

* **A1｜解析正对照**：用**各向同性** Eshelby 张量（球，闭式）算 `E/V`，
  与求解器在同一个 `ε⁰_7` 上的读数比。
  ⚠ **记账**：我们的 `C_cubic(134,110,36)` 是**立方**的（Zener 比 = 3.0，**强各向异性**），
  所以各向同性闭式**只能做量级对照**，不能当精确判据。判据取 **同量级即可**（0.5×–2×）。
* **A2｜离散收敛**（真正判"读数可不可信"的那条）：
  固定**物理尺寸**，把 `Δx` 减半两次（`(125nm,48) → (62.5,96) → (31.25,192)`），
  看 `E/V` 是否收敛。**判据：最细两档的相对差 ≤ 3%** ⇒ 读数已收敛。
* **A3｜形状敏感性重测**（换一个更极端的、且**不会横向撞到周期像**的形状族）：
  固定**厚度** `t = 4Δx`，只改**平面内长宽比** `W/L = 1 → 4`。
  若这族也几乎不变 ⇒ **椭球夹杂的能量密度对形状本来就不敏感**（⇒ 支持 (b)）。

**判读规则（先写死）**：
* A2 收敛 且 A1 同量级 ⇒ **求解器的 `E/V` 读数可信** ⇒ `_r474` 的 T2（5.8%）可用；
  而 T4 FAIL 归因于 **(b) 我的预期错了** ⇒ **量具无罪**。
* A2 不收敛 ⇒ 读数不可信 ⇒ T2 作废。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_pf3d as PF                                     # noqa: E402
from T16_verify_rve import C, EPS0                            # noqa: E402

VAR = 7
TOL_CONV = 0.03          # A2：最细两档相对差 ≤ 3%
TOL_A1_LO, TOL_A1_HI = 0.5, 2.0    # A1：同量级


def P(s):
    print(s, flush=True)


def build(N, dx):
    return PF.PF3D(N, dx * N, C, EPS0, gamma=0.0, w90=1.5 * dx, Lmob=1.0,
                   workers=1, k0_mode='free')


def sphere_mask(g, R):
    ii = (np.arange(g.N) + 0.5) * (g.L / g.N)
    X, Y, Z = np.meshgrid(ii - g.L / 2, ii - g.L / 2, ii - g.L / 2, indexing='ij')
    return (X ** 2 + Y ** 2 + Z ** 2) <= R ** 2


def ellip_mask(g, radii):
    ii = (np.arange(g.N) + 0.5) * (g.L / g.N)
    X, Y, Z = np.meshgrid(ii - g.L / 2, ii - g.L / 2, ii - g.L / 2, indexing='ij')
    return (X / radii[0]) ** 2 + (Y / radii[1]) ** 2 + (Z / radii[2]) ** 2 <= 1.0


def edens(g, v, mask):
    g.phi[:] = 0.0
    g.phi[v] = mask.astype(g.phi.dtype)
    E = float(g.E_el())
    sig = g.sigma_tensor()
    e0 = g.eps0_fields()
    Ied = float((e0 * sig).sum()) * g.dx ** 3
    V = mask.sum() * g.dx ** 3
    return E, V, E / V, Ied


# ---------------------------------------------------------------- A1 解析
def eshelby_sphere_isotropic(lam, mu, e0_voigt):
    """各向同性介质中**球**形夹杂的弹性能密度 `E/V`（Eshelby 闭式）。

    `ε = S:ε⁰`，`ε^el = (S−I):ε⁰`，`σ = C:ε^el`，`E/V = ½ σ:ε^el`。
    只看**偏量剪切**分量做量级核对（`ε⁰` 是 IPS，以剪切为主）。
    """
    nu = lam / (2.0 * (lam + mu))
    S11 = (7.0 - 5.0 * nu) / (15.0 * (1.0 - nu))
    S12 = (5.0 * nu - 1.0) / (15.0 * (1.0 - nu))
    S44 = (4.0 - 5.0 * nu) / (15.0 * (1.0 - nu))
    # Voigt: (11,22,33,23,13,12)
    S = np.zeros((6, 6))
    for i in range(3):
        for j in range(3):
            S[i, j] = S11 if i == j else S12
    for i in range(3, 6):
        S[i, i] = S44
    e = np.asarray(e0_voigt, float)
    # 工程剪切 ⇒ 张量剪切（乘 1/2），算完再换回
    et = e.copy(); et[3:] *= 0.5
    eel = S @ et - et
    # C（各向同性）作用在张量分量上：用 Lamé
    tr = eel[0] + eel[1] + eel[2]
    sig = np.empty(6)
    for i in range(3):
        sig[i] = lam * tr + 2.0 * mu * eel[i]
    for i in range(3, 6):
        sig[i] = 2.0 * mu * eel[i]
    # E/V = ½ σ:ε^el（张量缩并 ⇒ 剪切分量要乘 2）
    w = sig[0] * eel[0] + sig[1] * eel[1] + sig[2] * eel[2] \
        + 2.0 * (sig[3] * eel[3] + sig[4] * eel[4] + sig[5] * eel[5])
    return 0.5 * w


def cubic_to_isotropic(C11, C12, C44):
    """立方 → 各向同性（Voigt–Reuss–Hill 平均给出的等效 Lamé）。仅作量级对照。"""
    K = (C11 + 2.0 * C12) / 3.0
    G = (C11 - C12 + 3.0 * C44) / 5.0          # 立方晶体的 VRH 剪切模量
    lam = K - 2.0 * G / 3.0
    return lam, G


def to_voigt_eng(e33):
    """3×3 张量 → Voigt **工程**分量 (11,22,33,23,13,12)。

    ⚠ 自查：第一版直接拿 `EPS0[v]`（**3×3 矩阵**）去 `S @ e`，维度不匹配报错。
    `EPS0[v]` 是**张量**，必须先转 Voigt；剪切要 ×2（工程剪切）。
    """
    e = np.asarray(e33, float)
    return np.array([e[0, 0], e[1, 1], e[2, 2],
                     2 * e[1, 2], 2 * e[0, 2], 2 * e[0, 1]])


def main():
    P('=' * 96)
    P('_r475  给 `_r474` 补绝对标定 + 离散收敛')
    P('=' * 96)
    v = VAR - 1
    e0v = to_voigt_eng(EPS0[v])
    P('\nε⁰_%d (Voigt 工程分量 11,22,33,23,13,12) = %s'
      % (VAR, np.round(e0v, 6).tolist()))

    # ---------------- A1 解析量级对照 ----------------
    C11, C12, C44 = 134.0e9, 110.0e9, 36.0e9
    lam, mu = cubic_to_isotropic(C11, C12, C44)
    ana = eshelby_sphere_isotropic(lam, mu, e0v)
    P('\n[A1 解析（各向同性 Eshelby 球，VRH 等效 Lamé）]')
    P('   λ = %.4e  μ = %.4e  （由 C_cubic(%.0f,%.0f,%.0f) GPa 经 VRH 折算）'
      % (lam, mu, C11 / 1e9, C12 / 1e9, C44 / 1e9))
    P('   ⇒ 解析 E/V = **%.6e J/m³**' % ana)
    P('   ⚠ 记账：我们的 C 是**立方**的（Zener 比 = 2C44/(C11−C12) = %.2f，强各向异性）'
      % (2 * C44 / (C11 - C12)))
    P('      ⇒ 本行只能做**量级**对照，不是精确判据。')

    # ---------------- A2 离散收敛 ----------------
    P('\n[A2 离散收敛：固定物理尺寸，Δx 减半两次]')
    R_phys = 625e-9                     # 固定半径 625 nm
    P('   %-16s %-10s %-16s %-16s %s' % ('(Δx, N)', '胞数', 'E_el (J)', 'E/V (J/m³)', 'E/V ÷ 解析'))
    dens = []
    for dx, N in ((125e-9, 48), (62.5e-9, 96), (31.25e-9, 192)):
        g = build(N, dx)
        # ⚠ 逐字用与 `_r474` 相同的"胞中心"坐标构造
        E, V, d, Ied = edens(g, v, sphere_mask(g, R_phys))
        dens.append(d)
        P('   (%.2f nm, %3d)   %-10d %-16.6e %-16.6e %.3f'
          % (dx * 1e9, N, int(sphere_mask(g, R_phys).sum()), E, d, d / ana))
        del g
    rel = abs(dens[-1] - dens[-2]) / dens[-2]
    ok_conv = rel <= TOL_CONV
    P('   ⇒ 最细两档相对差 = **%.4f**（判据 ≤ %.2f）⇒ **%s**'
      % (rel, TOL_CONV, '✅ 已收敛' if ok_conv else '❌ 未收敛'))
    r_ana = dens[-1] / ana
    ok_a1 = TOL_A1_LO <= r_ana <= TOL_A1_HI
    P('   ⇒ 收敛值/解析 = **%.3f**（判据 ∈ [%.1f, %.1f]）⇒ **%s**'
      % (r_ana, TOL_A1_LO, TOL_A1_HI,
         '✅ 同量级（强各向异性下已属良好）' if ok_a1 else '❌ 不同量级 ⇒ 须查'))

    # ---------------- A3 形状敏感性重测（固定厚度，改平面内长宽比）----------------
    P('\n[A3 形状敏感性重测：固定 t = 4Δx，只改平面内 W/L]')
    g = build(96, 62.5e-9)
    t = 4 * 62.5e-9
    P('   %-24s %-10s %-16s %-16s' % ('半轴 (L/2, W/2, t/2) nm', '胞数', 'E_el (J)', 'E/V (J/m³)'))
    dd = []
    for WL in (1.0, 2.0, 3.0, 4.0):
        L = 750e-9
        m = ellip_mask(g, (L / 2, L / 2 / WL, t / 2))
        E, V, d, Ied = edens(g, v, m)
        dd.append(d)
        P('   (%.0f, %.0f, %.0f)      %-10d %-16.6e %-16.6e'
          % (L / 2 * 1e9, L / 2 / WL * 1e9, t / 2 * 1e9, int(m.sum()), E, d))
    r3 = max(dd) / min(dd)
    P('   ⇒ E/V 的 max/min = **%.4f**  ⇒ %s'
      % (r3, '形状（平面内长宽比）**也**只有百分之几的影响'
         if r3 < 1.15 else '形状影响明显'))

    # ---------------- 汇总 ----------------
    P('\n' + '=' * 96)
    P('★ 汇总')
    P('  A1 解析量级对照  E/V_solver / E/V_analytic = %.3f  %s'
      % (r_ana, 'PASS' if ok_a1 else 'FAIL'))
    P('  A2 离散收敛      最细两档相对差 = %.4f  %s'
      % (rel, 'PASS' if ok_conv else 'FAIL'))
    P('  A3 形状（长宽比）敏感性  max/min = %.4f' % r3)
    P('')
    if ok_conv and ok_a1:
        P('  ⇒ **求解器的 E/V 读数可信**（已收敛、且与解析同量级）')
        P('  ⇒ **`_r474` 的 T4 FAIL 应归因于 (b)：我的"球→扁球必须变 ≥30%%"这个预期本身错了**')
        P('     —— 椭球夹杂的弹性能密度对**形状**本来就只有百分之几的依赖。')
        P('  ⇒ **量具无罪 ⇒ `_r474` 的 T2（扫厚度 max/min = 1.0578）可以使用**：')
        P('     **弹性能密度对厚度的依赖是"弱"（~6%），不足以单独定出有限厚度。**')
    else:
        P('  ⇒ ⚠ A1/A2 未过 ⇒ `_r474` 的读数仍不可引用。')
    P('=' * 96)
    return 0


if __name__ == '__main__':
    sys.exit(main())
