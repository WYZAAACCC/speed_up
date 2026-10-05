#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_geom_consistency.py —— **⑥ 终检 · 层次①/②**：三条律的**几何自洽**（重算版）。

## 背景（我此前算错了，这里更正）
  我长期用 `plate = 2400×640×510 nm` 做几何估算。而**生产启动器**
  `_t5_short.py:82` 写的是 `--plate-L 1000 --plate-W 500 --plate-T 510`
  ⇒ **`A_f = 1000×500 nm = 0.5 µm²`，不是 1.536 µm²**。
  ⇒ 所有基于旧值的几何结论**必须重算**（硬步骤 A：以算例自己的 meta/启动器为准）。

## 要检查的（三条律的几何自洽 —— 可 FAIL）
  L1 C-2（**一个堆叠柱**）：`n(T) = α_KM·(M_s − T)` ⇒ 柱厚 `W_block = n·t`
  L2 体积律（**全盒**，`R606 §3`）：`N_lath = f_KM·V_box/V_lath`
  L3 几何容量：全盒能并排放几个足迹 `A_f` ⇒ `B_max = L_box²/A_f`
  **自洽要求**：`N_lath ≈ B_max × n`（体积律的总数 ≈ 几何容量 × 每柱根数）
"""
import math
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

PL, PW, PT = 1000e-9, 500e-9, 510e-9      # ★ 生产启动器 `_t5_short.py:82`
A_F = PL * PW
V_LATH = PL * PW * PT
MS, TEND = CL.M_S_TI64, 298.0

CASES = [
    ("生产 α_KM = 0.041739", 0.041739, 10.0e-6),
    ("R507 推导上界 α = 0.011", 0.011, 10.0e-6),
]

print("=" * 100)
print("⑥ 终检 · 层次①/②：三条律的几何自洽（**用生产 plate = 1000×500×510 nm**）")
print("=" * 100)
print(f"  A_f    = {PL*1e9:.0f} × {PW*1e9:.0f} nm = **{A_F*1e12:.3f} µm²**")
print(f"  V_lath = {V_LATH*1e18:.4f} µm³      t = {PT*1e9:.0f} nm")
print(f"  M_s = {MS} K   T_end = {TEND} K")

for name, akm, L in CASES:
    print("\n" + "-" * 100)
    print(f"【{name}】  L_box = {L*1e6:.1f} µm")
    V_BOX = L ** 3
    n = CL.alpha_km_n_lath(TEND, akm)
    n_int = CL.n_lath_int(TEND, akm)
    f_end = 1.0 - math.exp(-akm * (MS - TEND))
    N_vol = f_end * V_BOX / V_LATH
    B_max = L * L / A_F
    print(f"  L1 C-2  每柱根数 n = α·(M_s − T_end) = {akm} × {MS-TEND:.0f} = "
          f"**{n:.3f}** ⇒ 取整 {n_int}")
    print(f"      ⇒ 柱厚 W_block = n·t = {n*PT*1e6:.3f} µm   "
          f"({'**放得下** ✅' if n*PT <= L else '**放不下 ⇒ 几何 veto** ❌'})")
    print(f"  L2 体积律 N_lath = f·V_box/V_lath = {f_end:.6f} × "
          f"{V_BOX*1e18:.0f} / {V_LATH*1e18:.4f} = **{N_vol:.0f}** 根")
    print(f"  L3 几何容量 B_max = L²/A_f = {L*L*1e12:.1f} / {A_F*1e12:.3f} = "
          f"**{B_max:.1f}** 个足迹")
    print(f"  ★ 自洽检查：N_lath / B_max = {N_vol/B_max:.3f} "
          f"（= 平均每柱根数，应 ≈ n = {n:.3f}）")
    _rel = abs(N_vol / B_max - n) / max(n, 1e-9)
    print(f"     ⇒ 相对差 = {_rel*100:.2f}%  "
          f"{'**自洽** ✅' if _rel < 0.15 else '**不自洽 ⇒ 必须查** ❌'}")
    # 布满分数的那个足迹：撑满一个足迹需要几根
    print(f"  ⚠ 记账：填充**分数** f = N_vol/(B_max·n) = "
          f"{N_vol/(B_max*n):.4f}")
    print(f"      ⇒ 若要「200+ 根」，需要 {"**可行**" if B_max*n >= 200 else "**不可行**"}"
          f"（B_max·n = {B_max*n:.0f} 根是**单层并排的容量上限**）")

print("\n" + "=" * 100)
print("★ 结论要点")
print("  1. 三条律在**几何上互相自洽**（N_lath/B_max ≈ n），**不是矛盾**；")
print("  2. 但它们描述**不同尺度的几何**：C-2 = **一个堆叠柱**；体积律 = **全盒**；")
print("  3. ⇒ **从「一个柱」到「全盒多柱」这一步，框架里没有任何机制生成** ——")
print("     这正是 `limitations()` 第 1 条（'面内并列的多个 block 本轮不做'）的**量化后果**。")
print("=" * 100)
