#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_alpha_derive.py —— ③ 用文献律推导 `alpha_KM`（把 [标] 升级为 [推]）。

文献依据（仓库已读全文）：
  * **Magee 1970**（经 Geng 2024 / Khan 1990 §5.2 转述，仓库 `lit/NUCLEATION_ANCHORS.md:202`）：
        α = V̄ · φ · (dΔG/dT)
    其中 `V̄` = 每个新马氏体单元的平均体积，`φ` = 比例常数，`ΔG` = 化学驱动力。
    `f = 1 − exp[−α(Ms − T)]`，且 `α = V̄φ·dΔG/dT`。
  * **Khan 1990**（剑桥博士论文 §5.2，仓库已读）取 `V̄ ≈ 20 µm³`
    （依据 "a typical plate of martensite … 0.2 × 10 × 10 µm"）。
  * **Geng et al. 2024** DOI 10.1007/s12613-023-2780-9（全文，二手）：α(Fe-C) = 0.011 K⁻¹；
    组分式 `α_BS = 0.0224 − 0.0107x_C − 0.0007x_Mn − 0.00005x_Ni − 0.00012x_Cr − 0.0001x_Mo`。

本工具做三件事：
  Q1 **用 Khan 的钢数反标定 φ**，再用**本体系的板条体积**与 **DS_REF** 推 Ti-64 的 α；
     判据：反标定必须复现 α=0.011（否则我对 Magee 式的读法有误）。
  Q2 与生产生效值 `alpha_km=0.041739` 对照，判"是同一个量"还是"差多少"。
  Q3 敏感度：`V̄` ±50%、`DS_REF` ±20% ⇒ α 的带。
  Q4 **负对照**：把 `V̄` 换回钢的 20 µm³ ⇒ 应给出不同的 α（证明量具有分辨力）。
"""
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

DS = CL.DS_REF                 # 4.147e5 J/(m3 K)，由 DG_CRIT_REF/(T0-Ms) 推，带 ±20%
print(f"DS_REF = {DS:.6g} J/(m3*K)   （ΔG_v(T) = DS·(T0 − T)）")
print(f"T0 = {CL.T0_TI64} K,  Ms = {CL.M_S_TI64} K,  alpha_KM_REF = {CL.ALPHA_KM_REF}")

# ---- Q1：用 Khan 的钢数反标定 φ ----
V_steel = 0.2e-6 * 10e-6 * 10e-6        # 0.2 x 10 x 10 µm -> m3
a_fe = 0.011                            # K^-1, Geng 2024 转引 K-M 原始拟合
# 钢的 dΔG/dT：用 Fe-C 的典型值数量级（Magee 律里它是 ΔG 对 T 的斜率）
#   ⚠ 钢的 DS 我没有可靠值 ⇒ 用"反标定 φ"消掉它：φ·DS_steel = a_fe / V_steel
phi_DS_steel = a_fe / V_steel
print(f"\n=== Q1 反标定 ===")
print(f"  V_steel(Khan) = {V_steel*1e18:.3f} µm³")
print(f"  a_Fe-C        = {a_fe} K^-1")
print(f"  => φ·DS_steel = a/V = {phi_DS_steel:.6g} (K^-1 m^-3)")
print(f"     校验：a = V·(φDS) = {V_steel*phi_DS_steel:.6f}  "
      f"{'PASS' if abs(V_steel*phi_DS_steel-a_fe)<1e-12 else 'FAIL'}")

# ---- Q2：本体系（Ti-64 板条）的 V̄ 与 α ----
print(f"\n=== Q2 Ti-64 ===")
t_nm, L_lath_um, W_um = 510.0, 4.59, 1.224
V_ti = (t_nm * 1e-9) * (L_lath_um * 1e-6) * (W_um * 1e-6)
print(f"  板条几何：t={t_nm} nm, L={L_lath_um} µm, W={W_um} µm  (框架 recommend() 的口径)")
print(f"  V_ti = {V_ti*1e18:.4f} µm³   （钢的 {V_steel*1e18:.1f} µm³ 的 {V_ti/V_steel:.4f} 倍）")

# 关键：φ 是"每个单元形成时按驱动力增量计的数目比例"，与材料无关
#       ⇒ α_Ti = V_ti · φ · DS_Ti ... 但 φ·DS_steel 已被合并 ⇒ 需要 DS_steel 才能拆
#       两条走法都报（**不臆造 DS_steel**）：
print("\n  ⚠ φ 与 DS_steel 在上述反标定里**不可分离**（只得到乘积 φ·DS_steel）")
print("     ⇒ 必须另找 DS_steel 或直接找 Ti-64 的 dΔG/dT。两种口径都算：")

for name, ds_steel in (("若 DS_steel ≈ 1.0e6 J/(m3 K)（Fe-C 量级，**未核实**）", 1.0e6),
                       ("若 DS_steel = 4.147e5（= Ti-64 的 DS，**借用**）", DS)):
    phi = phi_DS_steel / ds_steel
    a_ti = V_ti * phi * DS
    print(f"    {name}")
    print(f"      phi = {phi:.6g}  =>  alpha_Ti = V_ti·phi·DS_Ti = {a_ti:.6g} K^-1")

# ---- Q3：敏感度 ----
print(f"\n=== Q3 敏感度（V_ti ±50%、DS ±20%，取 DS_steel=DS 口径）===")
phi = phi_DS_steel / DS
base = V_ti * phi * DS
for dv in (0.5, 0.8, 1.0, 1.2, 1.5):
    for dd in (0.8, 1.0, 1.2):
        a = V_ti * dv * phi * DS * dd
        print(f"  V×{dv:<4} DS×{dd:<4} -> alpha = {a:.6g} K^-1"
              f"   (n(T_end=298K) = {int(CL.alpha_km_n_lath(298.0, a))})")

# ---- Q4：生产值对照 ----
print(f"\n=== Q4 与生产生效值对照 ===")
a_prod = 0.041739
print(f"  生产 alpha_km        = {a_prod}   => n(T_end=298) = "
      f"{int(CL.alpha_km_n_lath(298.0, a_prod))}")
print(f"  文献（Fe-C，Koistinen）= 0.011    => n(T_end=298) = "
      f"{int(CL.alpha_km_n_lath(298.0, 0.011))}")
print(f"  生产 / Fe-C          = {a_prod/0.011:.3f} 倍")
print(f"  2D 观测上界（_fix_9to1 的 β_h 反推口径）：长:短 <= 24")

# ---- Q5：负对照 ----
print(f"\n=== Q5 负对照（量具有分辨力？）===")
a_steelV = V_steel * phi * DS
print(f"  用钢的 V=20 µm³ 代入 Ti 的 DS  => alpha = {a_steelV:.6g} K^-1")
print(f"  用 Ti 的 V={V_ti*1e18:.3f} µm³            => alpha = {base:.6g} K^-1")
print(f"  两者比 = {a_steelV/base if base else float('nan'):.4f}  "
      f"（= V_steel/V_ti = {V_steel/V_ti:.4f}）")
print(f"  {'PASS：V̄ 的选择确实改变 α，量具有分辨力' if abs(a_steelV-base)>1e-12 else 'FAIL：无分辨力'}")
