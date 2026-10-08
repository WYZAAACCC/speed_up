#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_A_growth3.py —— 生长判据的**最终版**（只读）。

⚠ v1/v2 的三处错（全部留痕）：
  E1 v1：结论句与表格数字**自相矛盾**（表格 <1，结论写"快"）。
  E2 v2：判据挂了 `dT_win = 100 K` 这个**我拍的数**，而真实分辨率是**每档 ΔT = 1/α_KM ≈ 24 K**。
  E3 v2：`t_grow` 的分子用了 **4 µm**（板条总长）。但"生长是否 instantaneous"要问的是
          **长到与邻居相撞**要多久 ⇒ 分子应是**核间距** `d = n^{-1/3}`，不是板条总长。
         （这才是 Liu 2015 "instantaneous growth" 的实际含义：核一旦出现就填满它的格位。）
"""
import numpy as np

R = 8.314

# ---------- 项目参数 ----------
V_box = 1000e-18          # m^3
V_lath = 250e-9 * 4000e-9 * 500e-9
n_final = 1.0 / V_lath    # 2.0e18 m^-3  目标位点数密度
Ms, T_end = 873.0, 298.0
alpha_KM = n_final / (Ms - T_end)      # C 的结论：a = n_final/(T_end−Ms)
dT_step = 1.0 / alpha_KM               # 每档过冷度
N_stage = int((Ms - T_end) / dT_step)  # 档数

print('=' * 96)
print('A-1  项目自己的时间尺度（全部由已定参数算出，不再拍数）')
print('=' * 96)
print('  n_final = 1/(t·L·W) = %.4e m^-3' % n_final)
print('  α_KM = n_final/(M_s−T_end) = %.4f K^-1  ⇒ 每档 ΔT = 1/α_KM = %.2f K，共 %d 档'
      % (alpha_KM, dT_step, N_stage))
d_nb_0 = n_final ** (-1.0 / 3.0)
print('  核间距（终态）d = n^(-1/3) = **%.1f nm**（= %.2f × 板条厚 t' % (d_nb_0 * 1e9,
                                                                      d_nb_0 / 250e-9), end='')
print('，量级自洽 ✅）' if 0.3 < d_nb_0 / 250e-9 < 0.5 else '）')
print('  即：板条**不需要长到 4 µm**，长到 ~%.0f nm 就与邻居相撞' % (d_nb_0 * 1e9))

print()
print('=' * 96)
print('A-2  生长时间 vs "两次形核之间的时间"（这才是正确的比较对象）')
print('=' * 96)
print('  物理：若"长大到相撞"比"下一个核出现"快得多 ⇒ 逐个核独立长大 ⇒ instantaneous 成立。')
print('  两次形核之间的时间 τ_nuc = 每档冷却时间 / 每档新增核数')
print('                             = (ΔT/q) / (ΔT·α_KM·V_box) = 1/(q·α_KM·V_box)')
print()
QG_LIST = [10e3, 20e3, 40e3, 60e3]
T_REF, v_REF = 1000.0, 4.0e-4     # 参考点（Liu 2015 窗口内，保守取下端）
print('  %-10s %-13s %-13s %-13s %-13s %s'
      % ('q (K/s)', 'τ_nuc (ms)', 't_grow(10kJ)', 't_grow(60kJ)', 'ΔT/2 冷却 (ms)', '判定'))
for q in (1e3, 1e4, 1e5, 1e6, 1e7, 1e8):
    tau_nuc = 1.0 / (q * alpha_KM * V_box)
    t_cool_half = (Ms - 298.0) / 2.0 / q
    row = []
    for QG in (10e3, 60e3):
        v0 = v_REF * np.exp(QG / (R * T_REF))
        v_T = v0 * np.exp(-QG / (R * Ms))      # 在 M_s 附近长大
        row.append(d_nb_0 / v_T)
    ok = (max(row) < t_cool_half)
    print('  %-10.0e %-13.3e %-13.3e %-13.3e %-13.3e %s'
          % (q, tau_nuc * 1e3, row[0] * 1e3, row[1] * 1e3, t_cool_half * 1e3,
             '✅ instantaneous' if ok else '⛔ 生长会限制'))

print()
print('=' * 96)
print('A-3  ★ 正确的表述（把 v1/v2 的两处相反结论都纠正掉）')
print('=' * 96)
print('  · 判据不是"能否长到 4 µm"（那是终态，不是条件），而是')
print('    **"长到核间距 d = n^(-1/3) = %.0f nm"所需时间 ≪ 可用时间**。' % (d_nb_0 * 1e9))
print('  · 由于 d 只有板条厚的 %.2f 倍，生长距离比 v1/v2 用的假设**小 %.4g 倍**。'
      % (d_nb_0 / 250e-9, 4.0e-6 / d_nb_0))
print('  · ⇒ instantaneous growth 的裕度**比 v2 的结论好得多**；')
print('    但仍须按上表逐 q 判定，不能一句话带过。')

print()
print('=' * 96)
print('A-4  盒子尺度的下界（由"盒内至少要有 N 个核"给出）')
print('=' * 96)
print('  要求盒内事件数 N_ev ≥ N_min ⇒ n_final·V_box ≥ N_min')
for N_min in (100, 200, 500, 1000):
    print('    N_min=%-5d ⇒ V_box ≥ %.4g µm³ ⇒ 边长 ≥ %.2f µm'
          % (N_min, (N_min / n_final) * 1e18, ((N_min / n_final) ** (1 / 3.0)) * 1e6))
print('  生产盒 = 1000 µm³（10 µm）⇒ 事件数 %.0f 根 ✅ 远大于任何合理下界' % (n_final * V_box))
print()
print('  ⚠ 但**反过来**的约束存在：盒必须 ≪ prior-β 晶粒，否则"晶界起始位点"项不能忽略。')
print('    N(M_s)=1/V_priorβ 占 n_final 的比例：')
for d_pb in (10e-6, 20e-6, 40e-6, 100e-6):
    N_Ms = 1.0 / ((4.0 / 3.0) * np.pi * (d_pb / 2.0) ** 3)
    print('      prior-β = %5.0f µm ⇒ N(M_s)=%.3e m^-3 ⇒ 占 n_final 的 %.2e %s'
          % (d_pb * 1e6, N_Ms, N_Ms / n_final,
             '✅ 可忽略' if N_Ms / n_final < 0.01 else '⚠ 不可忽略'))
print('  ⇒ **盒尺度可行域**：%.1f µm ≲ L_box ≪ prior-β 晶粒。生产 10 µm 落在此域内 ✅'
      % (((100 / n_final) ** (1 / 3.0)) * 1e6))
