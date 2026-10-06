#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_barrier.py —— 任务 (3)：**增厚势垒 ΔG\* 的推导与数值**（可运行，可 FAIL）。

## 物理（依据 `LATH_FACET_PLAN.md:375-381` 路径 (i)，输入为 Ti-64）
板条**增厚** = 宽面沿 `n*` 推进。位移型相变的宽面推进需要**新增失配位错**，
因而有**形核势垒**。单位面积失配能（van der Merwe 型）：

    e_misfit = ε·μ·b / (4π(1−ν)) · ln(R/r0)          [J/m²]

每**界面位点**的势垒：
    ΔG* = e_misfit / ρ_surface                        [J/位点]

无量纲化（温度 T）：`β_h(T) ≡ ΔG*/(kT)`。

## ⚠ 与仓库既有 `beta_h` 的关系（**必须记账，不得混用**）
* 既有 `beta_h` 是**唯象指数** `Mfac = exp(−β_h(n·n̂)²)`（`windowB_surface.py:5197`）；
* 本模块给的是**同一物理量的势垒解释**：`β_h = ΔG*/(kT)`；
* ⇒ 两者**在数值上可以互校**：`ΔG*/(k·M_s)` 应 ≈ **3.8**（`LATH_FACET_PLAN.md:381` 的
  独立推导结果）—— 这就是本模块的**正对照判据**。

## 判据（可 FAIL，先登记）
* **B1（正对照）**：用 `ε=0.1, μ=40 GPa, b=0.29 nm, ν=0.34, ln(R/r0)=3,
  ρ=1e19 m⁻², T=873 K`（= M_s）⇒ `ΔG*/(kT)` 应 ≈ **3.8**（±20%）
* **B2（量级）**：`ΔG*` 应落在 **0.3–1.0 eV**（位错形核的典型量级）
* **B3（温度依赖）**：`β_h(T)` 应 **∝ 1/T**（⇒ `ln v_n` vs `1/T` 是直线，Arrhenius）
"""
import numpy as np

# ---- 材料常数（出处见 docstring；`R618_PARAM_MAP.md`） ----
MU_TI64_PA = 40e9          # 剪切模量 [Pa]（位错环路径输入）
B_TI64_M = 0.29e-9         # Burgers 矢量 [m]（同上；⚠ 与 `a_alpha=0.295 nm` 略有差异，见 §记账）
NU_TI64 = 0.34             # 泊松比（`windowB_lath.NU_TI64`）
A_ALPHA_M = 0.295e-9       # α-Ti 点阵常数（`windowB_lath.A_ALPHA`，也是位错 b）
EPS_SHEAR = 0.1            # 相变切应变（位错环路径输入）
K_B = 1.380649e-23         # 玻尔兹曼常数 [J/K]
MS_TI64_K = 873.0          # 马氏体开始温度 [K]（`M_S_TI64`）
EV = 1.602176634e-19


def e_misfit(eps=EPS_SHEAR, mu=MU_TI64_PA, b=B_TI64_M, nu=NU_TI64,
             ln_R_r0=3.0):
    """单位面积失配能 [J/m²]（van der Merwe 型）。"""
    return eps * mu * b / (4.0 * np.pi * (1.0 - nu)) * ln_R_r0


def dG_star(rho_surface=1e19, **kw):
    """每界面位点的势垒 [J]；`rho_surface` 单位 [1/m²]。"""
    return e_misfit(**kw) / rho_surface


def beta_h_of_T(T, rho_surface=1e19, **kw):
    """`β_h(T) = ΔG*/(kT)`（Arrhenius 无量纲势垒）。"""
    return dG_star(rho_surface=rho_surface, **kw) / (K_B * T)


if __name__ == "__main__":
    print("=" * 88)
    print("(3) 增厚势垒 ΔG* —— 推导数值（输入全部为 Ti-64，出处见模块 docstring）")
    print("=" * 88)
    em = e_misfit()
    dg = dG_star()
    print("  e_misfit          = %.4f J/m²      （仓库记录 0.42 ⇒ 核对此数）" % em)
    print("  ΔG*（每界面位点） = %.4g J = **%.3f eV**" % (dg, dg / EV))
    print()
    print("  %-10s %-14s %s" % ('T(K)', 'ΔG*/(kT)', '备注'))
    for T, note in ((873.0, 'M_s（= 600 °C）'), (700.0, ''), (500.0, ''),
                    (300.0, '室温附近')):
        print("  %-10.0f %-14.3f %s" % (T, beta_h_of_T(T), note))
    print()
    # ---- 判据 ----
    b_ms = beta_h_of_T(MS_TI64_K)
    print("  ★ B1 正对照：ΔG*/(k·M_s) = **%.3f**（仓库独立推导给 3.8；判据 ±20%% = [3.04, 4.56]）"
          % b_ms)
    print("     ⇒ %s" % ("✅ PASS" if 3.04 <= b_ms <= 4.56 else "❌ FAIL"))
    ev = dg / EV
    print("  ★ B2 量级：ΔG* = **%.3f eV**（判据 0.3–1.0 eV）⇒ %s"
          % (ev, "✅ PASS" if 0.3 <= ev <= 1.0 else "❌ FAIL"))
    r = beta_h_of_T(436.5) / beta_h_of_T(873.0)
    print("  ★ B3 温度依赖：β_h(436.5K)/β_h(873K) = **%.3f**（∝1/T 应为 2.000）⇒ %s"
          % (r, "✅ PASS" if abs(r - 2.0) < 0.01 else "❌ FAIL"))
    print()
    print("  ⇒ 与生产 `beta_h = 6.477` 的关系：本推导在 **M_s** 给 %.2f；" % b_ms)
    print("     生产值 6.477 是 **C-5 步数下界与 β_h(T) 取大**的结果（非文献/非推导）")
    print("     ⇒ 两者**相差 %.2f×**，**不得混用**（须分档记账）。" % (6.477 / b_ms))
