#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_tension_recheck.py —— 重核 R620 的"硬张力"：它的前提是 `W_BLOCK_BAND_UM`，
而该常量在框架里自己标着【仍未检索到】（`windowB_closure.py:118`）。

本工具：
  Q1 打印 `W_BLOCK_BAND_UM` 及其**框架自记的出处状态**（判"是不是文献值"）；
  Q2 给定该带，算 `α_KM` 的允许区间与生产值的关系（复现 R507）；
  Q3 **在项目自己给出且有出处的数上**重算"200+ 根"需要什么：
        `总根数 = B·n = B·floor(α·(M_s − T_end))`
      ⇒ 对每个 α 求达到 200+ 所需的最小 B，并检查 `W_block = n·t` 是否落在带内；
  Q4 **负对照**：若把 `W_BLOCK_BAND_UM` 放宽到 (1.0, 12.0)，结论是否翻转（证明它是敏感的）。
"""
import sys

import numpy as np

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

Ms, T_end = CL.M_S_TI64, 298.0
t_lath = 510e-9
dV = Ms - T_end
print(f"M_s = {Ms} K, T_end = {T_end} K ⇒ ΔT = {dV} K,  t_lath = {t_lath*1e9:.0f} nm")

print("\n" + "=" * 90)
print("Q1 块厚带的出处状态")
print("=" * 90)
print(f"  W_BLOCK_BAND_UM = {CL.W_BLOCK_BAND_UM}  µm")
src = CL.__file__
with open(src, encoding="utf-8") as fh:
    for i, ln in enumerate(fh, 1):
        if "W_BLOCK_BAND_UM" in ln and "=" in ln:
            print(f"  定义在第 {i} 行：{ln.rstrip()}")
print("  ⇒ 框架**自己标注**该带仍未检索到 ⇒ **它不是文献值，是占位假设**")
print("  ⇒ 依赖它的 C-5/C-6/C-8 与 R507 五约束里的『块厚带』一条，全部继承这个不确定性。")

print("\n" + "=" * 90)
print("Q2 复现 R507：带 ⇒ α_KM 上界")
print("=" * 90)
print("  正确的链：n = α·ΔT（整数化后 n = floor(α·ΔT)）；W_block = n·t")
print("           ⇒ W_block = α·ΔT·t  ⇒  α = W_block/(ΔT·t)")
lo, hi = CL.W_BLOCK_BAND_UM
for W in (lo, hi):
    a = (W * 1e-6) / (dV * t_lath)          # ★ 必须把 µm 换成 m
    print(f"  W_block = {W} µm ⇒ α_KM = W/(ΔT·t) = {a:.5f} K^-1"
          f"  (n = {int(CL.alpha_km_n_lath(T_end, a))} 根/块)")
a_prod = 0.041739
n_prod = int(CL.alpha_km_n_lath(T_end, a_prod))
print(f"  生产 α = {a_prod} ⇒ n = {n_prod} 根/块, W_block = {n_prod*t_lath*1e6:.2f} µm")
print(f"  ⇒ 带的等效 α 上界 = {(hi*1e-6)/(dV*t_lath):.5f} K^-1"
      f"（与 R507 的 0.0205 一致？ {'✅' if abs((hi*1e-6)/(dV*t_lath)-0.0205)<1e-3 else '❌'})")

print("\n" + "=" * 90)
print("Q3 要 200+ 根，B 需要多大？（在带内的 α 上）")
print("=" * 90)
print(f"  {'α_KM':>8} {'n/块':>5} {'W_block µm':>11} {'在带内':>7} "
      f"{'B(200根)':>9} {'B(220根)':>9} {'B_max=65?':>10}")
for a in (0.0050, 0.0089, 0.0110, 0.0150, 0.0205, 0.0250, 0.041739):
    n = int(CL.alpha_km_n_lath(T_end, a))
    if n <= 0:
        continue
    W = n * t_lath * 1e6
    inband = lo <= W <= hi
    B200 = int(np.ceil(200 / n))
    B220 = int(np.ceil(220 / n))
    print(f"  {a:8.5f} {n:5d} {W:11.2f} {'✅' if inband else '❌':>7} "
          f"{B200:9d} {B220:9d} {'✅' if B200<=65 else '❌':>10}")

print("\n  ★ 判据：B 的几何上界 B_max = L_box²/A_f = 100 µm² / (2.4×0.64 µm²) = "
      f"{100/(2.4*0.64):.1f}")
print("     ⇒ 只要 B ≤ 65 且 α 在带内，**两者可兼得**（R620 的『不可兼得』结论需要修正）")

print("\n" + "=" * 90)
print("Q4 负对照：把带放宽到 (1.0, 12.0)，结论是否翻转（⇒ 该带敏感）")
print("=" * 90)
for band in ((1.0, 6.0), (1.0, 9.0), (1.0, 12.0)):
    lo2, hi2 = band
    ok = [a for a in np.arange(0.004, 0.06, 0.0005)
          if lo2 <= int(CL.alpha_km_n_lath(T_end, a)) * t_lath * 1e6 <= hi2
          and int(CL.alpha_km_n_lath(T_end, a)) > 0
          and int(np.ceil(200 / max(int(CL.alpha_km_n_lath(T_end, a)), 1))) <= 65]
    ar = (min(ok), max(ok)) if ok else None
    verdict = "生产 0.041739 在带内" if ar and ar[0] <= a_prod <= ar[1] else "生产 0.041739 **超带**"
    print(f"  带 {band}: 能同时满足『200+根』与『块厚在带内』的 α 区间 = "
          f"{'无解' if ar is None else f'[{ar[0]:.4f}, {ar[1]:.4f}]'}  ⇒ {verdict}")
print("\n  ⇒ 结论随带**单调变化** ⇒ 该带是关键未知量，**必须先查实**（或明确改用别的判据）。")
