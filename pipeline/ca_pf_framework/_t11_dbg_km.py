#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbg_km.py —— 查 `_t11_consistency.py` 的 ③（自洽检查 1）为何给出负增量。"""
import math
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

AKM, MS, TEND = 0.041739, CL.M_S_TI64, 298.0
T1 = CL.T_of_k(1, AKM)
t_hi, t_lo = T1, T1 - 1.0 / AKM
n_blk_int = CL.n_lath_int(TEND, AKM)

print("类型检查")
print(f"  T1      = {T1!r}   type={type(T1).__name__}   __len__? "
      f"{hasattr(T1, '__len__')}")
print(f"  t_hi    = {t_hi!r}")
print(f"  t_lo    = {t_lo!r}")
print(f"  1.0/AKM = {1.0/AKM!r}")
print(f"  n_blk_int = {n_blk_int!r}  type={type(n_blk_int).__name__}")
print(f"  M_S_TI64 = {MS!r}")

f_hi = 1 - math.exp(-AKM * (MS - t_hi))
f_lo = 1 - math.exp(-AKM * (MS - t_lo))
print(f"\n  f_hi (T={t_hi:.3f}) = {f_hi!r}")
print(f"  f_lo (T={t_lo:.3f}) = {f_lo!r}")
print(f"  逐档分数增量 = f_hi − f_lo = {f_hi - f_lo!r}")
print(f"  × n_blk_int = {(f_hi - f_lo) * n_blk_int!r}")

d_c2 = CL.alpha_km_n_lath(t_hi, AKM) - CL.alpha_km_n_lath(t_lo, AKM)
print(f"\n  C-2 首档增量 = {d_c2!r}")
print(f"  alpha_km_n_lath(t_hi) = {CL.alpha_km_n_lath(t_hi, AKM)!r}")
print(f"  alpha_km_n_lath(t_lo) = {CL.alpha_km_n_lath(t_lo, AKM)!r}")

print("\n★ 期望：M_s − T_1 = 1/α = 23.958 ⇒ f_hi = 1−e^(−1) = 0.6321")
print(f"  实测 f_hi = {f_hi:.6f}   {'对' if abs(f_hi-0.6321)<1e-3 else '**不对 ⇒ 查 T1**'}")
print(f"  M_s − T_1 = {MS - t_hi!r}   应为 23.958")
