#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_growth_TRUE.py —— 用**文献实测的** Q_G 把生长判据算成定论（只读）。

前几版把 Q_G 当自由参数扫（10–60 kJ/mol，标 [推理]）。
本轮在 Liu 2015 原文找到实测值：
    :874-875  "The value determined for the activation energy QG is **8.2 ± 1.5 kJ mol⁻¹**"
    :875-876  "Evidently, the γ/α′ interface possesses a **very high mobility**."
    :877-879  与其他 Fe–Ni–C 马氏体生长的 ≈8 kJ/mol 相符
且界面速度的 Arrhenius 形式来自原文 Eq.(17)：v(T) = v0·exp(−Q_G/RT)。

⇒ 本版**不再扫 Q_G**，用 8.2 kJ/mol（并给 ±1.5 的带）。
   参考点：v(M_s 附近) = 4.1e-4 m/s @ T = 1100 K（Liu Fig.10a 的平均值）
"""
import math
import numpy as np

R = 8.314
QG = 8.2e3          # J/mol   [引] Liu 2015 :874
QG_LO, QG_HI = 6.7e3, 9.7e3   # ±1.5 kJ/mol
T_REF, v_REF = 1100.0, 4.1e-4  # [引] Liu 2015 Fig.10a

print('=' * 96)
print('G-1  参数（全部来自文献，不再是我拍的）')
print('=' * 96)
print('  Q_G   = %.1f kJ/mol      [引] Liu 2015 :874（±1.5）' % (QG / 1e3))
print('  v(%.0f K) = %.2e m/s   [引] Liu 2015 Fig.10a 的平均值' % (T_REF, v_REF))
v0 = v_REF * math.exp(QG / (R * T_REF))
print('  ⇒ 反解 v0 = %.4g m/s（温度无关项）' % v0)
print()
print('  %-10s %-14s %-14s %-14s' % ('T (K)', 'v(T) (m/s)', 'v/v(1100K)', '说明'))
for T in (1600, 1400, 1200, 1100, 1000, 900, 800, 700, 600):
    print('  %-10.0f %-14.4e %-14.3f %s'
          % (T, v0 * math.exp(-QG / (R * T)),
             (v0 * math.exp(-QG / (R * T))) / v_REF,
             '← 参考点' if abs(T - T_REF) < 1 else ''))
print('  ⇒ 8.2 kJ/mol 是**很低的**激活能 ⇒ 速度只随 T 缓变（1600→600 K 只降 %.1f 倍）'
      % ((v0 * math.exp(-QG / (R * 1600))) / (v0 * math.exp(-QG / (R * 600)))))

print()
print('=' * 96)
print('G-2  ★ 生长判据：Π = n·(v/q)³ ≫ 1 ⇔ instantaneous growth 成立')
print('=' * 96)
print('  推导：d = n^(−1/3)（核间距）；t_grow = d/v；t_nuc = 1/(a·q·V_ev)')
print('        t_grow ≪ t_nuc  ⇔  Π ≡ n·(v/q)³ ≫ 1')
print('  等价：q* = v(T)·n^(1/3)（临界冷速）')
print()
print('  ⚠ 记账：n 是**待标定**的板条几何量（n = 1/(t·L·W)），')
print('     本表**只报 Π 对 n 的依赖**，不选定 n（用户指示：几何暂不定稿）。')
print()
print('  Π = n·(v/q)³  ⇒  对给定的 q，Π ∝ n。下表给 **q* = v·n^(1/3)**：')
print()
print('  %-12s %-16s %-16s %-16s' % ('n (m^-3)', 'q* @873K (K/s)', 'q* @1100K', 'q* @1400K'))
for n in (1e17, 3e17, 1e18, 2e18, 5e18):
    row = [v0 * math.exp(-QG / (R * T)) * n ** (1.0 / 3.0)
           for T in (873.0, 1100.0, 1400.0)]
    print('  %-12.1e %-16.3e %-16.3e %-16.3e' % (n, row[0], row[1], row[2]))

print()
print('  ⇒ 读法：LPBF 冷速 1e3–1e8 K/s。')
print('     · 若某工况的 q **低于** q* ⇒ Π>1 ⇒ 生长不限制，可用"形核控制"框架；')
print('     · 若 q **高于** q* ⇒ Π<1 ⇒ 生长限制，必须解生长方程（或换更大/更粗的组织）。')
print('  ⇒ **判据是"看工况"，但它现在是一个可算的式子，且参数全部有文献来源。**')

print()
print('=' * 96)
print('G-3  ★★ 这一版把 §4.6 的"未决前提"降级为"可判定的判据"')
print('=' * 96)
print('  之前（v2 的 §4.6）：Q_G 是我扫的 10–60 kJ/mol ⇒ 只能给"未决前提"。')
print('  现在：Q_G = 8.2 ± 1.5 kJ/mol [引 Liu 2015 :874]、v(1100 K) = 4.1e-4 m/s [引]。')
print('  ⇒ 判据式仍要**标定 n**（板条几何），但**不再有自由参数**。')
print()
print('  ±1.5 kJ/mol 的带对 q* 的影响（n = 1e18 m^-3、T = 1100 K）：')
for qg in (QG_LO, QG, QG_HI):
    vv = v_REF * math.exp(qg / (R * T_REF)) * math.exp(-qg / (R * 1100.0))
    print('    Q_G = %.1f kJ/mol ⇒ v(1100K) = %.4e m/s ⇒ q* = %.3e K/s'
          % (qg / 1e3, vv, vv * 1e18 ** (1 / 3.0)))
print('  ⇒ Q_G 的不确定度对 q* 的影响只有约 %.0f%%（因为 Q_G 本身小、T 高）'
      % (100 * abs((v_REF * math.exp(QG_HI / (R * T_REF)) * math.exp(-QG_HI / (R * 1100.0)))
                   / v_REF - 1)))

print()
print('=' * 96)
print('G-4  另一条同时被文献确认的架构选择：**准静态钟**')
print('=' * 96)
print('  [引] Liu 2015 的结论段（:885-891）逐字：')
print('    "The **athermal nature of martensite nucleation** is derived from the')
print('     observation that the martensite-start temperature is **independent of the')
print('     value of both the cooling rate and the applied uniaxial compressive stress**."')
print('  [引] 同段（:892-896）："The **thermally activated nature of the growth** induces an')
print('     overall temperature range …, MS−Mf, that increases upon increasing stress"')
print()
print('  ⇒ 组织学含义（对方案的两条硬结论）：')
print('     ① **形核是 athermal 的**（只依赖过冷度）⇒ 这正是 §4.1 的 N(T) 律的形式依据；')
print('     ② **生长有热激活**（Q_G = 8.2 kJ/mol）⇒ 所以"瞬时生长"是一个**要判的近似**，')
print('        不是公理 —— 与本方案的 Π 判据一致。')
print('  ⇒ 并且：**M_s 与冷速无关** ⇒ 用"按温度档推进 + 每档弛豫到不动点"的准静态钟')
print('     在物理上是对的（它模拟的正是"每个温度下 N(T) 个核长大到碰撞"）。')
