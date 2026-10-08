#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_growth_TRUE3.py —— 生长判据（**删掉伪交叉验证后的定稿版**，只读）。

⚠ **v2 的错误必须点名**（留痕，不抹）：
  我在 `_goal_growth_TRUE2.py` 里用**两个跨合金**的温度点
      (1100 K, 4.1e-4 m/s, Fe–0.7Al) 与 (500 K, 8.0e-4 m/s, Fe–10Ni–C)
  去拟合 Arrhenius，得到 **Q_G = −5.1 kJ/mol（负值！）**，
  然后在输出里写"与文献值吻合到 162%" —— **那是把矛盾当成吻合，属于自欺**。
  **跨合金的两点不能这样拟合**：两合金的 v0 与 Q_G 都不同，
  低温那个是**另一个合金**的，不能用来说明 Fe–0.7Al 的温度依赖。
  ⇒ 本版**删掉该拟合**，只保留有出处的东西。

正确的做法：**只用 Liu 2015 在单一合金（Fe–0.7Al）内部反解的结果**
  · Q_G = 8.2 ± 1.5 kJ/mol          [:874，由其 Fig.11 的 Arrhenius 图反解]
  · 并与 Fe–10.2at%Ni–C 的 ≈8 kJ/mol **同类对照**（同文 :877-879 自己给的对照），
    ——这是"同量级互证"，**不是**我做的拟合。
"""
import math

R = 8.314
QG, QG_ERR = 8.2e3, 1.5e3        # [引] Liu 2015 :874
T_REF, v_REF = 1100.0, 4.1e-4     # [引] Liu 2015 Fig.10a（Fe–0.7Al 窗口内平均值）

print('=' * 96)
print('H-0  ⚠ 先把我 v2 的错误点名（它没进任何结论）')
print('=' * 96)
print('  v2 用两个**跨合金**点拟合 Arrhenius ⇒ Q_G = −5.1 kJ/mol（负值），')
print('  我却在输出里写"吻合 162%" ⇒ **把矛盾当吻合，是自欺，已删。**')
print('  正确做法：只用 Liu 在**单一合金内部**反解的值，并与同文的同类对照互证。')

print()
print('=' * 96)
print('H-1  唯一有出处的参数（全部来自 Liu 2015）')
print('=' * 96)
print('  Q_G = %.1f ± %.1f kJ/mol   [引] :874「The value determined for the activation '
      'energy QG is 8.2 ± 1.5 kJ mol⁻¹」' % (QG / 1e3, QG_ERR / 1e3))
print('  v(%.0f K) = %.2e m/s      [引] Fig.10a（Fe–0.7Al，σ=1.61 MPa 等的平均）'
      % (T_REF, v_REF))
print('  同类对照：Fe–10.2at%Ni–C 的 ≈8 kJ/mol   [引] :877-879（Liu 自己给的对照）')
print('  ⇒ 两个独立来源都是 ≈8 kJ/mol ⇒ **"Q_G ≈ 8 kJ/mol 量级"是可信的**；')
print('     但我**没有**做、也**不应该做**跨合金的拟合。')

v_of = lambda T, qg=QG: v_REF * math.exp(qg / (R * T_REF)) * math.exp(-qg / (R * T))
print()
print('  v(T) = %.4g · exp(−%.1f kJ/mol / RT)：' % (v_REF * math.exp(QG / (R * T_REF)), QG / 1e3))
for T in (1600, 1400, 1200, 1100, 900, 700, 600):
    print('    T=%4.0f K  v = %.4e m/s  （v/v(1100K) = %.3f）'
          % (T, v_of(T), v_of(T) / v_REF))
print('  ⇒ Q_G 小（8.2 kJ/mol）⇒ 速度只随 T 缓变（600→1600 K 仅 2.8 倍）。')

print()
print('=' * 96)
print('H-2  ★ 生长判据（定稿口径）')
print('=' * 96)
print('  Π = n·(v/q)³ ≫ 1  ⇔  instantaneous growth 成立；等价 q* = v(T)·n^(1/3)')
print('  ⚠ 唯一的待标定量是 **n（板条数密度）**；按用户指示，几何暂不定稿。')
print()
print('  %-12s %-14s %-14s %-14s' % ('n (m^-3)', 'q* @873K', 'q* @1100K', 'q* @600K'))
for n in (1e17, 3e17, 1e18, 2e18):
    print('  %-12.1e %-14.3e %-14.3e %-14.3e'
          % (n, v_of(873.0) * n ** (1 / 3.0), v_of(1100.0) * n ** (1 / 3.0),
             v_of(600.0) * n ** (1 / 3.0)))
print()
print('  Q_G 的 ±1.5 kJ/mol 带对 q* 的影响（正确算法：改变 Q_G 时**重解 v0**，')
print('  使 v(T_REF) 守恒 —— 因为 v_REF 是在 T_REF 处**测得**的）：')
print('    ⇒ 由上面的 v_of 定义可见：q*(T) 正比于 v(T)。')
print('      Q_G 从 6.7→9.7 时，v(600 K)/v(1100 K) = exp[(Q_G/R)(1/T_REF − 1/600)]：')
for qg in (6.7e3, QG, 9.7e3):
    ratio = math.exp((qg / R) * (1.0 / T_REF - 1.0 / 600.0))
    print('        Q_G=%.1f kJ/mol ⇒ v(600K)/v(1100K) = %.4f' % (qg / 1e3, ratio))
print('    ⇒ **在 1100 K 附近 Q_G 几乎不影响（<6%%）；往低温端外推时影响才放大。**')

print()
print('=' * 96)
print('H-3  ★★ 三条有文献支撑的硬结论（写进定稿）')
print('=' * 96)
print('  1) **形核是 athermal 的**（只依赖过冷度，不依赖时间）')
print('     [引] Liu 2015 :885-891：「The **athermal nature of martensite nucleation** is')
print('          derived from the observation that the martensite-start temperature is')
print('          **independent of the value of both the cooling rate and the applied')
print('          uniaxial compressive stress**.」')
print('     ⇒ 这是 `N(T) = N(M_s) + a(T − M_s)` 这一**形式**的依据。')
print()
print('  2) **生长是热激活的**（Q_G = 8.2 ± 1.5 kJ/mol，界面迁移率很高）')
print('     [引] :874-876「Evidently, the γ/α′ interface possesses a **very high mobility**」')
print('     ⇒ 所以"瞬时生长"是**要判的近似**（判据 Π / q*），不是公理。')
print()
print('  3) **准静态钟（每档弛豫到不动点）在物理上是对的**')
print('     [引] :885-896：M_s 与冷速/应力无关（形核侧）+ 热激活只把 M_s−M_f 拉宽（生长侧）')
print('     ⇒ "按温度档推进 + 每档弛豫"模拟的正是')
print('       「每个温度下 N(T) 个核各自长大到碰撞」这一瞬态。')
print()
print('  ⇒ 结果：v2 §4.6 里我只能标 [推理] 的那条，现在升级为')
print('     **有文献参数的判定式**；唯一剩余待标定量是 n。')
