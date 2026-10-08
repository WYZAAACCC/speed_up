#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_growth_final.py —— 生长判据的**无量纲收口**（只读）。

前面 v1–v4 的错（全部留痕于各脚本头）：结论与数字矛盾 / 挂手拍数 /
生长距离取错 / α_KM 与 a 量纲混用 / 核间距取终态 / µm³→m³ 差 1000。

本版只做一件事：把"生长是否限制环节"写成一个**无量纲数**，并逐参数扫描。
推导（3 句）：
  核间距            d = n^(-1/3)
  长到相撞的时间    t_grow = d / v
  该核形核后到下一个核出现的时间  t_nuc = 1/(n_dot·V_ev)   ，n_dot = dN/dt = a·q
  ⇒ 判据  t_grow ≪ t_nuc
     ⇔  n^(-1/3)/v ≪ 1/(a·q·V_ev)
     ⇔  **n·(v/q)³ ≫ 1/V_ev**
  取单位体积（V_ev=1）：**Π ≡ n·(v/q)³ ≫ 1  ⇔ 生长不限制**（instantaneous growth 成立）
运行： /root/miniconda3/envs/ml/bin/python -u _goal_growth_final.py
"""
import math
import numpy as np

R = 8.314
T_REF, v_REF = 1000.0, 4.0e-4      # [引] Liu 2015 窗口内

GEO = [('生产现值（代码） 250/4000/500 nm', 250e-9, 4.0e-6, 500e-9),
       ('文献中值 700/6300/700 nm', 700e-9, 6.3e-6, 700e-9),
       ('文献上沿 880/8000/890 nm', 880e-9, 8.0e-6, 890e-9)]


def v_of_T(T, QG):
    v0 = v_REF * math.exp(QG / (R * T_REF))
    return v0 * math.exp(-QG / (R * T))


print('=' * 98)
print('G-1  ★ 无量纲判据  Π = n·(v/q)³ ≫ 1  ⇔ 生长不限制（instantaneous growth 成立）')
print('=' * 98)
print('  推导：t_grow = n^(-1/3)/v ；t_nuc = 1/(a·q·V_ev)；令 t_grow ≪ t_nuc ⇒ Π ≫ 1/V_ev')
print('  n = 终态位点数密度；v = 界面速度(T)；q = 冷却速率')
print()
print('  %-34s %-10s %-12s %-12s %-12s %s'
      % ('几何', 'q (K/s)', 'Π(T=873K)', 'Π(T=1200K)', 'Π(T=1600K)', '判定(873K)'))
for tag, t, L, W in GEO:
    n = 1.0 / (t * L * W)
    for q in (1e4, 1e6, 1e8):
        pis = []
        for T in (873.0, 1200.0, 1600.0):
            v = v_of_T(T, 20e3)           # 取 Q_G = 20 kJ/mol 作代表
            pis.append(n * (v / q) ** 3)
        print('  %-34s %-10.0e %-12.3e %-12.3e %-12.3e %s'
              % (tag, q, pis[0], pis[1], pis[2],
                 '✅' if pis[0] > 1 else '⛔'))

print()
print('=' * 98)
print('G-2  等价形式（更好用）：把 q 反解成"临界冷速" q*')
print('=' * 98)
print('  Π = 1 ⇒ q* = v(T)·n^(1/3)   ——  低于 q* 时生长不限制')
print()
print('  %-34s %-14s %-14s %-14s' % ('几何', 'q*(873K)', 'q*(1200K)', 'q*(1600K)'))
for tag, t, L, W in GEO:
    n = 1.0 / (t * L * W)
    row = [v_of_T(T, 20e3) * n ** (1.0 / 3.0) for T in (873.0, 1200.0, 1600.0)]
    print('  %-34s %-14.3e %-14.3e %-14.3e' % (tag, row[0], row[1], row[2]))
print()
print('  ⇒ LPBF 的冷速区间是 1e3–1e8 K/s；上表的 q* 落在同一区间 ⇒')
print('    **能否假设 instantaneous growth 是"看工况"的，不是一个常数结论。**')

print()
print('=' * 98)
print('G-3  ★★ 结论（最终口径，写进方案）')
print('=' * 98)
print('  1) 判据不是"能不能长到 4 µm"，而是无量纲数')
print('        **Π = n·(v/q)³ ≫ 1**   （n=位点数密度，v=界面速度，q=冷速）')
print('     它同时包含"位点有多密""界面有多快""冷得有多快"三件事。')
print('  2) 用生产参数（n=2e18 m^-3、t=250 nm/L=4 µm/W=500 nm）与')
print('     v(1000 K)=4.1e-4 m/s [引]、Q_G=20 kJ/mol [推理]：')
n_prod = 1.0 / (250e-9 * 4e-6 * 500e-9)
for q in (1e4, 1e6, 1e8):
    pi = n_prod * (v_of_T(873.0, 20e3) / q) ** 3
    print('        q=%.0e K/s ⇒ Π = %.3e  %s' % (q, pi, '✅ 生长不限制' if pi > 1 else '⛔ 生长会限制'))
print('  3) ⇒ **这是一个"未决前提"，不是既成事实。**')
print('     方案必须：(a) 给出上面的检验式；(b) 明确取哪个 T 与 Q_G；')
print('     (c) 若 Π < 1，则**不得**用"形核控制"框架，必须解生长方程。')
print()
print('  ⚠ 三条记账：')
print('     · v(1000 K)=4.1e-4 m/s 是 Fe–0.7at%Al 的实测（Liu 2015）；Ti64 α′ 无同类实测。')
print('     · Q_G = 20 kJ/mol 是我取的包络中值 [推理]；Liu 2015 §5.3 有反解结果，本轮未读到数值。')
print('     · Π 对 v 是**三次方**敏感 ⇒ v 差 2 倍，Π 差 8 倍 ⇒ 必须先把这个速度测准。')
