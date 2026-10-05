#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_rac_derive.py --- ★ 自催化范围 `r_ac` 与「自然块数」的可复现推导

## 文献给的形式（R603，已取原文摘要）
Galindo-Nava & Rivera-Díaz-del-Castillo, Acta Mater. **98** (2015),
DOI 10.1016/j.actamat.2015.07.018：**block/packet 尺寸线性依赖原晶粒尺寸 `D`**
（本框架里 `D` 是物理输入，来自 Window A 的晶粒骨架）。

## 本方推的两件事
### (1) 自催化范围 `r_ac`
已成形板条（体积 `V_l`、相变应变 `ε⁰`）在距离 `r` 处的**远场应力提升**约
```
Δ(σ:ε⁰) ≈ μ ε⁰² · V_l / r³
```
自催化"起作用"的判据取**形核门槛本身** `f_crit = 2γ/t`（与引擎同一口径）：
```
μ ε⁰² · V_l / r_ac³ = f_crit        ⇒   r_ac = ( μ ε⁰² V_l / f_crit )^(1/3)
```
**⚠ 先要排除一个错阈值**：热涨落 `k_BT/V*` 在本温区比弹性能密度**小 10 个数量级**
⇒ 马氏体是 **athermal**，热激活不是这里的门槛 ⇒ 必须用 `f_crit`。

### (2) 自然块数
把 `r_ac` 当作自催化"畴"的尺度：
```
n_block^自然 ≈ V_box / ( (4/3)π r_ac³ )
```
**⇒ 这是"远场上限式"估计，不是结论性预言**（近场应力更大且有结构）。

## 判据（**可 FAIL**）
* **D1** 热涨落阈值确实远小于弹性能密度（⇒ 排除热涨落）；
* **D2** `r_ac` 落在盒子的(0, L] 内且量级合理；
* **D3** `n_block^自然` 与仿真实测 `nblk` **不一致** ⇒ 则**仿真的块数不是自催化畴**
  ⇒ 证据支持用户的质疑（块数是规定值）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
FAIL = []


def ck(name, cond, msg):
    print("  %-50s %s   %s" % (name, "✅ PASS" if cond else "❌ FAIL", msg))
    if not cond:
        FAIL.append(name)


print("══ 自催化范围 r_ac 与自然块数  ══\n")

# ── 从引擎/闭包模块取常数（取不到就用实测值并标明）──
K = {}
try:
    import windowB_closure as WC
    for nm in ("G_TI64", "NU_TI64", "E0_TI64", "GAMMA_M_TI64"):
        if hasattr(WC, nm):
            K[nm] = float(getattr(WC, nm))
    print("  从 windowB_closure 取到：%s" % {k: "%.4g" % v for k, v in K.items()})
except Exception as e:
    print("  ⚠ windowB_closure 取常数失败：%s ⇒ 用实测/文献值并标明" % e)

C11, C12, C44 = 134.0e9, 110.0e9, 36.0e9          # Ti64 β（WINDOWB_PARAMS.md:文献）
MU_V = (C11 - C12 + 3 * C44) / 5.0                  # Voigt 剪切模量
NU = 0.34                                           # 泊松比（典型 Ti64 β）
GAMMA = 0.20                                        # 界面能 J/m²（**占位，待核**）
T_NUC = 312.5e-9                                    # 核厚 = 250 + 62.5 nm（引擎口径）
mv = __import__("windowB_ti64_variants")
ALLV = np.asarray(mv.variants()[0], float)
I2 = np.eye(3)
E_DEV = float(np.linalg.norm(ALLV[0] - np.trace(ALLV[0]) / 3 * I2))
V_L = 1000e-9 * 500e-9 * 510e-9                      # 籽晶体积 m³
T_AG = 30e-9                                         # 板条厚度估计（核厚量级）
print("  用常数：μ_Voigt=%.3g Pa  ν=%.2f  γ=%.3f J/m²  t_nuc=%.1f nm  V_l=%.3g m³"
      % (MU_V, NU, GAMMA, T_NUC * 1e9, V_L))
print("          ‖dev ε⁰‖=%.4f（12 变体全同，已验）" % E_DEV)

# ── D1 排除热涨落 ──
f_crit = 2 * GAMMA / T_NUC
w_el = MU_V * E_DEV ** 2
kB_T = 1.380649e-23 * 849.0
th_dens = kB_T / V_L
print("\n  D1 阈值候选")
print("     f_crit = 2γ/t_nuc            = %.4e J/m³" % f_crit)
print("     弹性能密度 μ‖devε⁰‖²          = %.4e J/m³" % w_el)
print("     热涨落密度 k_BT/V_l            = %.4e J/m³" % th_dens)
ck("D1 热涨落远小于弹性能密度（排除热激活）",
   th_dens < 1e-6 * w_el,
   "热涨落/弹性能 = %.2e（差 %.0f 个数量级）"
   % (th_dens / w_el, np.log10(w_el / th_dens)))

# ── D2 r_ac ──
r_ac3 = w_el * V_L / f_crit
r_ac = r_ac3 ** (1.0 / 3.0)
# ★ 修（本会话第 15 次自查）：第一版写 `L = 1000e-6`（= 1 mm），
#   把盒子边长当成了 1000 µm ⇒ `n_nat` 虚高 1e6 倍（2.25e6 而非 2.25）。
#   实际盒子是 **10 µm = 1e-5 m**（N=160 × dx=62.5 nm）。
L = 10e-6
print("\n  D2 自催化范围")
print("     r_ac = ( μ‖devε⁰‖² · V_l / f_crit )^(1/3) = **%.4g m = %.3f µm**"
      % (r_ac, r_ac * 1e6))
print("     盒子边长 L = %.1f µm（N=160 × dx=62.5 nm）" % (L * 1e6))
ck("D2 r_ac 落在 (0, L] 内", 0 < r_ac <= L,
   "r_ac/L = %.3f" % (r_ac / L))

# ── D3 自然块数 vs 仿真 ──
n_nat = (L ** 3) / ((4.0 / 3.0) * np.pi * r_ac ** 3)
L_um = L * 1e6
n_for_B3 = 16      # t10PRT2 (B=3) 实测 nblk
n_for_B9 = 9       # t10B9 规定值（尚待跑完核实；此处按规定值）
print("\n  D3 自然块数 vs 仿真块数")
print("     n_block^自然 = V_box / ((4/3)π r_ac³) = **%.2f 个**" % n_nat)
print("     仿真实测（B=3 那跑）nblk = %d ；B=9 规定值 = %d" % (n_for_B3, n_for_B9))
ratio = n_for_B3 / max(n_nat, 1e-30)
ck("D3 自然块数与仿真块数一致（若不一致 ⇒ 仿真块数是规定值）",
   abs(np.log10(ratio)) < 0.5,
   "仿真/自然 = %.1f 倍 ⇒ %s"
   % (ratio, "一致" if abs(np.log10(ratio)) < 0.5 else
      "**不一致 ⇒ 证据支持「块数是规定值」**"))

# ── 反解：要让「自然」给出 200+ 板条，需要什么 ──
print("\n  ★ 反解（供 goal ③ 的判据用）")
for n_b in (2, 9, 16, 200):
    need_rac = (L ** 3 / n_b / ((4 / 3) * np.pi)) ** (1 / 3)
    print("     若自然块数 = %-4d ⇒ 需 r_ac = %.3f µm（现推得 %.3f µm）"
          % (n_b, need_rac * 1e6, r_ac * 1e6))
print("     ⇒ 现推得的 r_ac=%.2f µm 对应自然块数 ≈ %.1f；"
      "仿真给 %d ⇒ **块数由 B 规定，不是自催化畴**"
      % (r_ac * 1e6, n_nat, n_for_B3))
print()
print("  ⚠ 记账：γ=%.2f J/m² 与 ν=%.2f 是**占位值（待核出处）**；r_ac 对它们敏感"
      "（r_ac ∝ γ^(−1/3)）⇒ 本结论是**量级**判断，不是精确定值。" % (GAMMA, NU))
print()
print("  自检汇总：%s" % ("✅ 全部 PASS" if not FAIL else "❌ 失败项 = %s" % FAIL))
sys.exit(0 if not FAIL else 1)
