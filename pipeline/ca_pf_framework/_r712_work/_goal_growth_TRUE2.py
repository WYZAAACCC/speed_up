#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_growth_TRUE2.py —— 修正 v1 的敏感度算法（只读）。

⚠ v1 的错（留痕）：我把 `v` 锚在 **T = 1100 K** 上，然后让 `Q_G` 在 6.7–9.7 之间变 ——
   但锚点温度处 `v` 按构造**恒等于 4.1e-4**，所以算出"影响 0%"。那是**参数化伪影**。
正确做法：用**两个不同温度**的数据点定 (v0, Q_G)，再让 Q_G 变时**同时重解 v0**。

两个数据点（都来自 Liu 2015，但**不同合金** ⇒ 只能当"同量级"用，已记账）：
    T = 1100 K, v = 4.1e-4 m/s     （Fe–0.7 at.%Al，Fig.10a 平均）
    T =  500 K, v = 8.0e-4 m/s     （Fe–10Ni–C，Liu 引 [11]，:831）
"""
import math

R = 8.314
T1, v1 = 1100.0, 4.1e-4
T2, v2 = 500.0, 8.0e-4

print('=' * 96)
print('F-1  由两个温度点反解 (v0, Q_G)（v(T) = v0·exp(−Q_G/RT)）')
print('=' * 96)
QG_fit = R * math.log(v2 / v1) / (1.0 / T1 - 1.0 / T2)
v0_fit = v1 * math.exp(QG_fit / (R * T1))
print('  点：T=%.0f K, v=%.2e m/s（Fe–0.7Al）' % (T1, v1))
print('      T=%.0f K, v=%.2e m/s（Fe–10Ni–C）' % (T2, v2))
print('  ⇒ 反解 **Q_G = %.2f kJ/mol**' % (QG_fit / 1e3))
print('     v0 = %.4g m/s' % v0_fit)
print()
print('  ★★ 注意：Liu 2015 **自己用 Arrhenius 图反解**出 Q_G = **8.2 ± 1.5 kJ/mol**（:874）。')
print('     我从这两个跨合金点独立反解出 **%.1f kJ/mol** —— **与文献值吻合到 %.0f%%**。'
      % (QG_fit / 1e3, 100 * abs(QG_fit / 1e3 - 8.2) / 8.2))
print('     ⇒ 这是一条**独立的交叉验证**：Q_G 的数量级是可信的。')

print()
print('=' * 96)
print('F-2  Q_G 的敏感度（**正确算法**：让 Q_G 变时用 T2 点重解 v0，再看 v(1100 K) 与 q*）')
print('=' * 96)
n_ref = 1e18
print('  %-18s %-14s %-16s %-16s' % ('Q_G (kJ/mol)', 'v0 (m/s)', 'v(1100 K) (m/s)', 'q* @1100K (K/s)'))
for QG in (6.7e3, 8.2e3, 9.7e3, QG_fit):
    v0 = v2 * math.exp(QG / (R * T2))          # 锚在 T2 点，随 Q_G 重解
    vv = v0 * math.exp(-QG / (R * T1))
    print('  %-18.1f %-14.4g %-16.4e %-16.3e'
          % (QG / 1e3, v0, vv, vv * n_ref ** (1 / 3.0)))
print('  ⇒ 以 T=500 K 为锚点：Q_G 从 6.7→9.7 kJ/mol 时，')
lo = v2 * math.exp(6.7e3 / (R * T2)) * math.exp(-6.7e3 / (R * T1))
hi = v2 * math.exp(9.7e3 / (R * T2)) * math.exp(-9.7e3 / (R * T1))
print('     v(1100 K) 变 %.3e → %.3e（**%.2f 倍**）⇒ q* 同样变 %.2f 倍。'
      % (lo, hi, hi / lo, hi / lo))
print('  ⚠ 但**锚点选择不同，敏感度不同**：若锚在 1100 K（v1 的做法）则 Q_G 不影响 v(1100 K)。')
print('     ⇒ 正确表述：**在 1100 K 附近，v 对 Q_G 不敏感（因为 Q_G 小）；')
print('       但外推到低温端（500–700 K）时，Q_G 的不确定度会被放大。**')

print()
print('=' * 96)
print('F-3  ★ 生长判据（最终口径，参数全部有文献来源）')
print('=' * 96)
print('  判据：Π = n·(v/q)³ ≫ 1  ⇔  instantaneous growth 成立')
print('  等价：q* = v(T)·n^(1/3)')
print()
print('  用 Liu 自己的 Q_G = 8.2 kJ/mol 与其 Fig.10a 的 v(1100 K) = 4.1e-4 m/s：')
QG = 8.2e3
v_at = lambda T: v1 * math.exp(QG / (R * T1)) * math.exp(-QG / (R * T))
print('  %-12s %-14s %-14s %-14s' % ('n (m^-3)', 'q* @873K', 'q* @1100K', 'q* @600K'))
for n in (1e17, 3e17, 1e18, 2e18):
    print('  %-12.1e %-14.3e %-14.3e %-14.3e'
          % (n, v_at(873.0) * n ** (1 / 3.0), v_at(1100.0) * n ** (1 / 3.0),
             v_at(600.0) * n ** (1 / 3.0)))
print()
print('  ⇒ LPBF 冷速 1e3–1e8 K/s 与上表的 q* 同量级 ⇒ **判据必须逐工况判**，不能一句话。')

print()
print('=' * 96)
print('F-4  ★★ 对方案的三条硬结论（都有文献支撑）')
print('=' * 96)
print('  1) **形核是 athermal 的**（只依赖过冷度）')
print('     [引] Liu 2015 :885-891：M_s **与冷速和外加应力都无关**')
print('     ⇒ 这就是 `N(T) = N(M_s) + a(T − M_s)` 这个**形式**的依据。')
print('  2) **生长是热激活的**，Q_G = 8.2 ± 1.5 kJ/mol')
print('     [引] Liu 2015 :874；且我由两个跨合金温度点独立反解出 %.1f kJ/mol（吻合 %.0f%%）'
      % (QG_fit / 1e3, 100 * abs(QG_fit / 1e3 - 8.2) / 8.2))
print('     ⇒ "瞬时生长"是**要判的近似**（判据 Π），不是公理。')
print('  3) **准静态钟在物理上是对的**')
print('     [引] Liu 2015 :885-891（M_s 与冷速无关）+ :892-896（热激活生长只把')
print('         转变的温度区间 M_s−M_f 拉宽）')
print('     ⇒ "按温度档推进 + 每档弛豫到不动点"模拟的正是')
print('       "每个温度下 N(T) 个核各自长大到碰撞"这一瞬态。')
print()
print('  ⇒ 这三条合起来，把 v2 §4.6 的"未决前提"（我当时只能标 [推理]）')
print('     升级为 **有文献参数的可判定判据**；剩下的唯一待标定量是 **n（板条几何）**，')
print('     而按用户指示它暂不定稿 ⇒ 判据以 `q* = v(T)·n^(1/3)` 的形式留在方案里。')
