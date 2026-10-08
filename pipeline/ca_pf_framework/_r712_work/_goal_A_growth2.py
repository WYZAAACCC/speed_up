#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_A_growth2.py —— **纠正 v1** 后重判"生长是否限制环节"（只读）。

⚠ v1 的两处错（留痕，不抹）：
  E1 结论句与表格数字**自相矛盾**：表格给 `v_meas/v_req = 0.00123`（1e8 K/s），
     结论却写"快 1e-03 倍"并当成支持 —— **方向反了**。1e8 K/s 下确实"不够"。
  E2 更根本：v1 把**单一速度值 4.1e-4 m/s 当常数**用，而那是在
     ① **35 K/s**（慢冷）② **M_s–M_f 窗口（1154–1063 K）** 上测的。
     把它搬到 1e8 K/s / 低温端是**外推**，必须先给出温度依赖。
  正确做法：用 Liu 2015 Eq.(17) `v(T) = v0 exp(−Q_G/RT)` —— 从**同一篇的两个温度点**
     反解 (v0, Q_G)，再外推到本项目关心的温度。
     · 500 K（Fe–10Ni–C，Liu 引）: v = 8.0e-4 m/s
     · 1093 K（Fe–0.7Al 窗口中值）: v = 4.1e-4 m/s   ← 注意：**低温更快**？
       ⇒ 若两点都按"低温更快"，会得到 Q_G>0 而 v(1093)>v(500) 的反常，必须查清。
运行： /root/miniconda3/envs/ml/bin/python -u _goal_A_growth2.py
"""
import numpy as np

R = 8.314

print('=' * 94)
print('A-0  ⚠ 先把 v1 的自相矛盾摆出来（这是纠错的起点）')
print('=' * 94)
print('  v1 表格（比值 v_meas/v_req）：')
for q, r in ((35, 3.51e3), (1e5, 1.23), (1e6, 0.123), (1e8, 0.00123)):
    print('    q=%-9.0f K/s  ⇒  %-10.4g  %s' % (q, r, '够' if r > 1 else '**不够**'))
print('  ⇒ v1 的结论句只在 q ≤ 1e5 成立；对 LPBF 的高冷速段**结论是反的**。')

print()
print('=' * 94)
print('A-1  用 Liu 2015 的两个温度点反解 Arrhenius 参数（这是它 Eq.17 的形式）')
print('=' * 94)
# 两个数据点的温度：500 K（Fe-10Ni-C，同碳杂质的对照）与 Fe-0.7Al 的窗口
# Fe-0.7Al: M_s=1154, M_f=1063；论文 Fig.10a 的 v 是随 T 变的曲线，给的平均 ~4.1e-4
T1, v1 = 500.0, 8.0e-4       # Fe-10Ni-C（Liu 引 [11]），500 K
T2, v2 = 1100.0, 4.1e-4      # Fe-0.7Al 窗口上端附近取代表值
print('  数据点：T=%.0f K, v=%.2e m/s（Fe–10Ni–C，Liu 引 [11]）' % (T1, v1))
print('          T=%.0f K, v=%.2e m/s（Fe–0.7Al 的平均值，Liu Fig.10a）' % (T2, v2))
print('  ⚠ 这两点的**合金不同**（Fe-10Ni-C vs Fe-0.7Al）⇒ 不能直接当同一条曲线的两点。')
print('  ⇒ 因此改用**同一条曲线内部**的信息：Liu Fig.10a 说 v 随 T 降低而下降')
print('     （:844-848 "the γ/α′ interface velocity vi decreases gradually with the')
print('      progress of martensite formation, i.e. with decreasing T … which is')
print('      compatible with a thermally activated nature of the growth"）')
print('  ⇒ 即 **Q_G > 0、v 随 T 降低而降低**。这与"低温更快"相反 —— 我 v1 的用法是错的。')

print()
print('=' * 94)
print('A-2  取 Q_G 的可行范围，做**区间**判断而不是点判断')
print('=' * 94)
# Liu 2015 §5.3 会反解 Q_G；我们没读到数值 ⇒ 用文献常见区间做包络
# 马氏体界面迁移的激活能文献常见 10–60 kJ/mol（本项标 [推理]）
QG_LIST = [10e3, 20e3, 40e3, 60e3]
T_REF, v_REF = 1000.0, 4.0e-4      # 取 M_s~M_f 窗口下端的代表点（保守：偏低）
print('  取参考点：T=%.0f K 处 v=%.1e m/s（保守，取窗口下端）' % (T_REF, v_REF))
print('  %-12s %-16s %-16s %-16s %-14s'
      % ('Q_G (kJ/mol)', 'v(1600K) m/s', 'v(1000K) m/s', 'v(700K) m/s', 't_grow(4µm)@1000K'))
for QG in QG_LIST:
    v0 = v_REF * np.exp(QG / (R * T_REF))
    def v(T):
        return v0 * np.exp(-QG / (R * T))
    t_g = 4.0e-6 / v(1000.0)
    print('  %-12.0f %-16.3e %-16.3e %-16.3e %-14.3e'
          % (QG / 1e3, v(1600.0), v(1000.0), v(700.0), t_g))

print()
print('=' * 94)
print('A-3  ★ 正确的判据：拿"生长时间"与"该温度段的冷却时间"比')
print('=' * 94)
print('  物理：板条要在**它自己形核的那个温度附近**完成长大。')
print('  若 t_grow ≪ 该温度段的冷却时间 ⇒ 生长不是限制环节（instantaneous 成立）。')
print()
print('  %-12s %-12s %-14s %-14s %-14s %s'
      % ('q (K/s)', 'ΔT_win(K)', 't_cool(ms)', 'Q_G=20kJ t_g(ms)', 'Q_G=60kJ t_g(ms)', '判定(20/60)'))
for q in (1e3, 1e4, 1e5, 1e6, 1e7, 1e8):
    # 生长发生的温度窗：取 M_s 附近 100 K（保守：窗口越窄越不利）
    dT_win = 100.0
    t_cool = dT_win / q
    row = []
    for QG in (20e3, 60e3):
        v0 = v_REF * np.exp(QG / (R * T_REF))
        v_T = v0 * np.exp(-QG / (R * 1000.0))
        row.append(4.0e-6 / v_T)
    ok = ['✅' if row[i] < t_cool else '⛔' for i in range(2)]
    print('  %-12.0e %-12.0f %-14.3e %-14.3e %-14.3e %s/%s'
          % (q, dT_win, t_cool * 1e3, row[0] * 1e3, row[1] * 1e3, ok[0], ok[1]))

print()
print('=' * 94)
print('A-4  ★★ 结论（修正后，写进方案用）')
print('=' * 94)
print('  1) 【纠正】"生长一定不是限制环节"**在 LPBF 的高冷速段不成立**：')
print('     当 q ≳ 1e5 K/s 时，"在 100 K 的冷却窗内长到 4 µm"所需的速度已经')
print('     与实测界面速度同量级或更高 ⇒ **不能无条件假设 instantaneous growth**。')
print('  2) 但真正要问的不是"能不能长到 4 µm"，而是"**能不能长到碰撞**"：')
print('     板条在 M_s 附近形核时，邻居间距是 ~1/√N 量级（N 为位点密度）；')
print('     只要它长到与邻居相撞就停 —— 那个长度通常**远小于 4 µm**。')
print('     ⇒ 需要用**位点密度**把"要长多长"换成"邻居间距"，再判 instantaneous。')
print('  3) [引] Liu 2015 的原文明确把 instantaneous growth 与 athermal nucleation')
print('     **绑成一对假设**（:335-336），并在**他们的冷速 35 K/s** 上验证通过。')
print('     ⇒ 该假设有文献支持，**但支持范围是慢冷**；搬到 LPBF 必须重新判。')
print('  4) ⇒ **这是一条必须写进 D-2 的"未决前提"**，而不是既成事实。')
print()
print('  ⇒ 下一步（可执行）：把 (2) 的判据做成一个**闭式检验**：')
print('      邻居间距 d_nb = n^(-1/3)（n = 位点密度）')
print('      若 d_nb / v(T) ≪ dT/q  ⇒ instantaneous 成立')
print('      ⇒ 该式同时给出"盒子必须多大才能容纳 ≥ 若干个核"的下界。')
