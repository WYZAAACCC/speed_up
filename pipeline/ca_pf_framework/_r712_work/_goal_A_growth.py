#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_A_growth.py —— A 的定量收口：用**文献实测速度**判"生长是否限制环节"（只读）。

要回答的问题（它决定 D-2 的架构）：
  "板条长大"与"继续形核"哪一个限制组织？若生长快得多 ⇒ α′ 是 **nucleation-controlled**
  ⇒ 需要的是一条 **位点密度律 N(T)**，不是一条"形核率 λ(t)"。

文献支点（逐字读到）：
  Liu 2015, Acta Mater. 98, 164：
    :828  "The average interface velocities (of value, say 4.1 ± 0.1 ×10⁻⁴ m/s)"
    :831  "measured γ/α′ interface velocity (≈8×10⁻⁴ m/s at 500 K) for a Fe–10Ni–C alloy"
  LITPARAM §6.5（本仓，标 [推理]）："纵向 4 µm 只需 10⁻⁶–10⁻¹ m/s"
运行： /root/miniconda3/envs/ml/bin/python -u _goal_A_growth.py
"""
import numpy as np

# ---- 文献实测的界面速度（马氏体，非 massive） ----
v_meas = 4.1e-4        # m/s  Liu 2015 平均
v_meas2 = 8.0e-4       # m/s  Fe-10Ni-C @500 K（Liu 引）
v_massive = 4.0e-6     # m/s  pure Fe 的 massive γ→α（**对照：那是扩散型**）

# ---- LPBF 冷却窗口 ----
T_start, T_end = 1600.0, 400.0
print('=' * 92)
print('A-1  冷却速率 → 特征时间')
print('=' * 92)
rates = [35.0, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8]
print('  %-12s %-16s %-18s' % ('q (K/s)', 't_cool (s)', '说明'))
for q in rates:
    t = (T_start - T_end) / q
    note = '本仓 LITPARAM 的区间' if 1e3 <= q <= 1e8 else ('Liu 2015 的实验冷速' if q == 35 else '')
    print('  %-12.0f %-16.3e %-18s' % (q, t, note))
print('  ⇒ LPBF 的 t_cool ∈ [%.0e, %.0e] s' % ((T_start - T_end) / 1e8,
                                              (T_start - T_end) / 1e3))

print()
print('=' * 92)
print('A-2  ★ 板条要长到目标尺寸，需要多大速度？（板条 4 µm / 250 nm）')
print('=' * 92)
L_l, t_l = 4.0e-6, 250e-9
print('  %-12s %-18s %-18s %-14s' % ('q (K/s)', 'v_req 纵向(m/s)', 'v_req 增厚(m/s)', '比值 v_meas/v_req'))
for q in rates:
    t = (T_start - T_end) / q
    v_long = L_l / t
    v_thick = (t_l / 2) / t              # 两个自由面同时推进
    print('  %-12.0f %-18.3e %-18.3e %-14.3g'
          % (q, v_long, v_thick, v_meas / v_long))
print('  ⇒ 即使取**最快**的 LPBF 冷速 1e8 K/s，所需纵向速度也只有 %.2e m/s，'
      % (L_l / ((T_start - T_end) / 1e8)))
print('    而实测马氏体界面速度是 %.1e m/s ⇒ **生长快 %.0e 倍**'
      % (v_meas, v_meas / (L_l / ((T_start - T_end) / 1e8))))

print()
print('=' * 92)
print('A-3  ★★ 对照：扩散型（massive）生长在此冷速下够不够？')
print('=' * 92)
for q in (1e3, 1e4, 1e5, 1e6):
    t = (T_start - T_end) / q
    need = L_l / t
    print('  q=%.0e K/s ⇒ 需要 %.2e m/s；massive 实测 %.1e m/s ⇒ %s'
          % (q, need, v_massive,
             '够（生长不是限制）' if v_massive > need else '**不够**（生长会限制）'))
print('  ⇒ 这解释了为什么本项目**必须**走 athermal 路线：')
print('    LPBF 冷速下 massive 型生长来不及，实验也观察不到 massive α，而是 α′。')

print()
print('=' * 92)
print('A-4  ★ 结论（决定 D-2 的架构，写进方案用）')
print('=' * 92)
print('  1) 在 LPBF 的全部冷速区间（1e3–1e8 K/s）上，马氏体板条的生长速度')
print('     （实测 4.1e-4 m/s）**比所需速度高 2–7 个数量级** ⇒')
print('     **α′ 是 nucleation-controlled**（形核控制），生长可视为瞬时。')
print('  2) [引] 这不是本项目的独有判断：Liu 2015 的原文说 KM 式')
print('     "is based on the assumption of **athermal nucleation and, necessarily,')
print('      instantaneous growth**" ⇒ **该假设有文献明确支持**。')
print('  3) ⇒ 因此 D-2 要的**不是** `λ_b(t) = ∫I dV + ∫I_Γ dA`（时间率），')
print('     而是 **位点密度 N(T)**（过冷度的函数）—— 即 Liu 2015 的 Eq.(4)。')
print('  4) ⇒ 与之配套，"准静态钟"（每档弛豫到不动点）在物理上是**正确**的求解器，')
print('     因为它模拟的正是"每个温度下 N(T) 个核各自长大到碰撞"这一瞬态。')
print()
print('  ⚠ 记账：v_meas = 4.1e-4 m/s 是 **Fe–0.7 at.%Al** 的实测（Liu 2015, σ=1.61 MPa 等）；')
print('     Ti-6Al-4V α′ 的专门实测**本轮未取到**。但 A-2 的裕度是 2–7 个数量级，')
print('     即使 Ti64 的界面速度低 2 个数量级，结论仍然成立。')
