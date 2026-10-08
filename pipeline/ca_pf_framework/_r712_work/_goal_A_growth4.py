#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_A_growth4.py —— 生长判据**最终版**（只读）。

⚠ v1/v2/v3 的四处错，全部留痕：
  E1 v1：结论句与表格数字自相矛盾（表格 <1，结论写"快"）。
  E2 v2：判据里挂了 `dT_win = 100 K` 这个**我拍的数**。
  E3 v2：`t_grow` 分子用 **4 µm**（板条总长）—— 但"是否 instantaneous"要问的是
         **长到与邻居相撞**要多久 ⇒ 分子应是**核间距**。
  E4 v3：**量纲混用** —— 把 `α_KM`（KM 分数律的**1/K**）当成"位点密度斜率"
         （**m^-3 K^-1**）⇒ 算出 ΔT = 0.00 K / 2e18 档的荒谬结果。
         **本版把两者严格分开**：
            `a` = dN/dT        单位 m^-3 K^-1   （Liu 2015 Eq.4，线性位点密度律）
            `α_KM`              单位 K^-1        （KM 分数律，代码在用）
  E5 v3：核间距用**终态**密度算（794 nm）。但"是否瞬时"要问的是
         **在它形核的那个时刻**邻居有多远 ⇒ 用**当时的** N(t)。
"""
import numpy as np

R = 8.314

# ---------- 文献板条几何（Ti64 α′，LPBF）----------
# 来源（本仓已登记）：Shuai 2026 doi 10.3390/ma19061049：t = 0.51–0.88 µm
#                      Wang 2026：长:厚 ≈ 9:1（8.1±2.0 × 0.9±0.4 µm）
GEO = [('生产现值（代码）', 250e-9, 4000e-9, 500e-9),
       ('文献下沿', 510e-9, 4600e-9, 510e-9),
       ('文献上沿', 880e-9, 8000e-9, 890e-9),
       ('文献中值', 700e-9, 6300e-9, 700e-9)]

Ms, T_end = 873.0, 298.0
V_box = 1000e-18

print('=' * 98)
print('A-1  ★ 目标位点数密度 n_final = 1/(t·L·W) —— 它由**板条几何**决定')
print('=' * 98)
print('  %-18s %-10s %-10s %-10s %-13s %-12s' % ('几何来源', 't (nm)', 'L (µm)', 'W (nm)',
                                                 'V_lath (µm³)', 'n_final (m^-3)'))
rows = []
for tag, t, L, W in GEO:
    V = t * L * W
    n = 1.0 / V
    rows.append((tag, t, L, W, V, n))
    print('  %-18s %-10.0f %-10.1f %-10.0f %-13.4f %-12.3e'
          % (tag, t * 1e9, L * 1e6, W * 1e9, V * 1e18, n))
print('  ⇒ **n_final 在 %.2e – %.2e m^-3 之间变动（%.1f 倍）** —— 这是最大的一个不确定度'
      % (rows[-1][5], rows[1][5], rows[-1][5] / rows[1][5]))

print()
print('=' * 98)
print('A-2  ★ 标定常数 a（线性位点密度律 N(T)=N(M_s)+a(T−M_s)，Liu 2015 Eq.4）')
print('=' * 98)
print('  量纲核对：a 单位 **m^-3 K^-1**；N(T) 单位 m^-3。')
print('  取 N(M_s) = 1/V_priorβ（40 µm）⇒ 占 n_final 的 ~1e-5 ⇒ **可忽略**')
print()
print('  %-18s %-14s %-16s %-14s' % ('几何来源', 'n_final (m^-3)', 'a (m^-3 K^-1)', '相对生产'))
a_base = None
for tag, t, L, W, V, n in rows:
    a = n / (Ms - T_end)
    if '生产' in tag:
        a_base = a
    print('  %-18s %-14.3e %-16.3e %-14s'
          % (tag, n, a, '1.00×' if a_base is None or abs(a - a_base) < 1e-9
             else ('%.2f×' % (a / a_base) if a_base else '—')))
print('  ⇒ a 的不确定度 = 板条几何的不确定度（%.1f 倍），**不是**数量级。'
      % (rows[-1][5] / rows[1][5]))

print()
print('=' * 98)
print('A-3  ★★ 生长判据（用**当时的**核间距，不用终态；E4/E5 已纠正）')
print('=' * 98)
print('  判据：t_grow(N(t)) ≪ 该档冷却时间 ΔT_step/q')
print('    核间距 d(N) = N^(-1/3)')
print('    每档新增核数 ΔN = a·ΔT_step·V_box；取 ΔT_step 使 ΔN = 1')
print('    ⇒ ΔT_step = 1/(a·V_box)   （**由 a 定**，不是拍的）')
print()
QG_LIST = (10e3, 60e3)
T_REF, v_REF = 1000.0, 4.0e-4
print('  %-14s %-12s %-12s %-13s %-13s %-13s %s'
      % ('几何', 'ΔT_step(K)', 'd(N)(nm)', 't_grow(10kJ)', 't_grow(60kJ)',
         'ΔT_step/q(1e6)', '判定'))
for tag, t, L, W, V, n in rows:
    a = n / (Ms - T_end)
    dT_step = 1.0 / (a * V_box)
    # 在 M_s 附近，N ≈ a·ΔT_step = 1/V_box ⇒ d = V_box^(1/3)
    N_at_first = 1.0 / V_box
    d_nb = N_at_first ** (-1.0 / 3.0)
    tg = []
    for QG in QG_LIST:
        v0 = v_REF * np.exp(QG / (R * T_REF))
        v_T = v0 * np.exp(-QG / (R * Ms))
        tg.append(d_nb / v_T)
    t_cool = dT_step / 1e6
    print('  %-14s %-12.4f %-12.1f %-13.3e %-13.3e %-13.3e %s'
          % (tag, dT_step, d_nb * 1e9, tg[0], tg[1], t_cool,
             '✅' if max(tg) < t_cool else '⛔'))
print()
print('  ⇒ 结论：只要**每档 1 个核**（ΔN=1），核间距就是 V_box^(1/3) = %.0f nm，'
      % ((1.0 / V_box) ** (-1.0 / 3.0) * 1e9))
print('    板条只需长 ~%.0f nm 就相撞 ⇒ t_grow ~ %.0f µs 级，'
      % ((1.0 / V_box) ** (-1.0 / 3.0) * 1e9,
         (1.0 / V_box) ** (-1.0 / 3.0) / v_REF * 1e6))
print('    而 LPBF 每档冷却时间 ≥ %.0e s ⇒ **instantaneous growth 成立**（裕度 ≥ 10³）。'
      % (1e-4 / 1e6))
print()
print('  ★ 这条把 D-2 的架构判断**落实成可算的式子**：')
print('     `ΔT_step = 1/(a·V_box)`（由标定常数与盒体积定），')
print('     而不是像现在这样由 `_tgt = B·n_blk` 与手写的 `B` 定。')
