#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_c5.py —— ②-1：C-5 判据的量化判据。

要回答三个问题（每条给可 FAIL 的判据）：
  Q1 `beta_h_min` 在生产参数（N_steps=20000, Δx=62.5 nm, t=510 nm）下到底是多少？
     判据：应 ≈ 7.11（与 banner 自报一致）⇒ 判据的**算术**对不对。
  Q2 该下界对 `delta_max`（允许的相对增厚）的敏感性？
     判据：delta_max 0.3→0.1 时下界增加 ln(3)=1.0986。
  Q3 **生产实际会走多少步**？—— 只在 `qs_clock=1` 下：
     `qs_max_relax=100` × 温度档数 = 步数上界。
     判据：若实际步数 << 20000，则 banner 的告警**用错了步数轴**（数值判据 OK，套用口径错）。
"""
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

print("=== 常量 ===")
print("  CFL_DEFAULT =", CL.CFL_DEFAULT)
print("  ALPHA_KM_REF =", CL.ALPHA_KM_REF)
print("  T0_TI64 (Ms) =", CL.T0_TI64, "K")
print("  DS_REF =", CL.DS_REF, "J/(m3 K)")

print("\n=== Q1 beta_h_min 生产参数 ===")
rows = [
    (20000, 62.5e-9, 510e-9),
    (20000, 62.5e-9, 500e-9),
    (20000, 125e-9, 510e-9),
    (2300, 62.5e-9, 510e-9),
    (3600, 125e-9, 510e-9),
    (200, 62.5e-9, 250e-9),
]
for ns, dx, t in rows:
    print(f"  N_steps={ns:<6d} dx={dx*1e9:6.1f} nm  t={t*1e9:5.1f} nm"
          f"   dn=0.30 -> {CL.beta_h_min(ns, dx, t):7.4f}"
          f"   dn=0.10 -> {CL.beta_h_min(ns, dx, t, delta_max=0.1):7.4f}")

print("\n=== Q2 delta_max 敏感性（应满足 ln(0.30/0.10)=1.0986）===")
a = CL.beta_h_min(20000, 62.5e-9, 510e-9, delta_max=0.30)
b = CL.beta_h_min(20000, 62.5e-9, 510e-9, delta_max=0.10)
print(f"  delta_max=0.30 -> {a:.6f}")
print(f"  delta_max=0.10 -> {b:.6f}")
print(f"  差 = {b-a:.6f}   （理论 ln3 = 1.098612）  "
      f"{'PASS' if abs((b-a)-1.098612)<1e-5 else 'FAIL'}")

print("\n=== Q3 beta_h_of_T 物理形式 ===")
for T in (873.0, 700.0, 500.0, 298.0):
    print(f"  T={T:6.1f} K -> beta_h_of_T = {CL.beta_h_of_T(T):.4f}")

print("\n=== Q4 生产实际步数（qs_clock=1）===")
n = int(CL.alpha_km_n_lath(298.0, CL.ALPHA_KM_REF))
print(f"  n(T_end=298 K) = floor(alpha*(Ms-298)) = {n}")
print(f"  温度档数 = n = {n}（qs_dT = 1/alpha = {1/CL.ALPHA_KM_REF:.4f} K）")
print(f"  qs_max_relax = 100/档 ⇒ 步数上界 = {n*100} 步（不是 20000）")
print(f"  用 20000 步算出的下界 = {CL.beta_h_min(20000,62.5e-9,510e-9):.4f}")
print(f"  用 {n*100} 步算出的下界 = {CL.beta_h_min(n*100,62.5e-9,510e-9):.4f}")
