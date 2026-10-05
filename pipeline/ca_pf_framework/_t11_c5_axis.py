#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_c5_axis.py —— C-5 的**步数轴**对比（R619 ②-1 的更正量化）。"""
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

DX = 62.5e-9
T = 510e-9
ALPHA = 0.041739
MS = 873.0
TEND = 298.0
TSTART = MS - 1.0 / ALPHA          # T_1 = 849.04 K（时钟起点，见 R29）

n_stage = max(int((ALPHA * (TSTART - TEND)) // 1), 1)
b_wrong = CL.beta_h_min(20000, DX, T)
b_right = CL.beta_h_min(100 * n_stage, DX, T)

print("=" * 84)
print(f"dx={DX*1e9:.1f} nm   t={T*1e9:.0f} nm   α_KM={ALPHA}   M_s={MS}")
print(f"T_start = T_1 = M_s − 1/α = {TSTART:.3f} K ;  T_end = {TEND}")
print(f"档数 = floor(α·(T_start − T_end)) = {n_stage}")
print(f"真实步进轴（--qs-clock 1）= qs_max_relax(100) × 档数({n_stage}) "
      f"= {100*n_stage}")
print("=" * 84)
print(f"  beta_h_min(--steps 20000)        = {b_wrong:.4f}   ← 旧（**轴错**）")
print(f"  beta_h_min(qs_max_relax×档数)     = {b_right:.4f}   ← 新（**轴对**）")
print(f"  生产 --beta-h                    = 6.477")
print()
print(f"  旧轴判据：{b_wrong:.4f} > 6.477 ? "
      f"{'**违反 C-5**' if b_wrong > 6.477 else '满足'}")
print(f"  新轴判据：{b_right:.4f} > 6.477 ? "
      f"{'**违反 C-5**' if b_right > 6.477 else '**满足**'}")
print()
print("★ 结论：换成**正确的轴**后该算例 **不违反 C-5** ⇒ "
      "我早先那句\"β_h 因此不满足\"的推论**撤回**；")
print("  但\"banner 用错轴\"这条**成立** —— 两件事必须分开说。")
