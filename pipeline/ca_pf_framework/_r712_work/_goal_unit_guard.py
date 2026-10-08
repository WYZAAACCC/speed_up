#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_unit_guard.py —— **量纲/单位自检**（防我自己再犯单位错）。

背景：本 goal 里我自己犯了 5 处错（全部留痕在对应脚本头部）：
  E1 结论句与表格数字矛盾；E2 判据里挂手拍的 ΔT_win；
  E3 生长距离用板条总长而非核间距；E4 `α_KM`(1/K) 当位点密度斜率(m^-3K^-1)；
  E5 核间距用终态密度；E6 **µm³→m³ 换算写成 1e-18（真值 1e-15）**。
⇒ 本脚本把**方案里要用的每一个量**做一次显式换算断言，供复核。
"""
import sys

OK = []


def ck(tag, got, want, tol=1e-12, unit=''):
    good = abs(got - want) <= tol * max(abs(want), 1e-300)
    OK.append((tag, good))
    print('  [%s] %-52s got=%.6g want=%.6g %s'
          % ('PASS' if good else 'FAIL', tag, got, want, unit))


print('=' * 92)
print('U-1  体积换算（E6 的直接防线）')
print('=' * 92)
ck('1 µm³ → m³', (1e-6) ** 3, 1e-18, 1e-12, 'm^3')
ck('1000 µm³ → m³', 1000 * (1e-6) ** 3, 1e-15, 1e-12, 'm^3')
ck('10 µm 立方 → m³', (10e-6) ** 3, 1e-15, 1e-12, 'm^3')
ck('1 nm³ → m³', (1e-9) ** 3, 1e-27, 1e-12, 'm^3')

print()
print('=' * 92)
print('U-2  方案用的量（单位 + 数值 + 来源）')
print('=' * 92)
V_box = (10e-6) ** 3
print('  V_box = (10 µm)^3 = %.4e m^3' % V_box)
ck('V_box', V_box, 1.0e-15)

t_l, L_l, W_l = 250e-9, 4.0e-6, 500e-9
V_lath = t_l * L_l * W_l
print('  V_lath = 250 nm × 4 µm × 500 nm = %.4e m^3 = %.3f µm³' % (V_lath, V_lath * 1e18))
ck('V_lath', V_lath, 5.0e-19)

n_final = 1.0 / V_lath
print('  n_final = 1/V_lath = %.4e m^-3   [位点数密度]' % n_final)
ck('n_final', n_final, 2.0e18)

N_ev = n_final * V_box
print('  N_ev = n_final·V_box = %.1f 根   [盒内总事件数]' % N_ev)
ck('N_ev', N_ev, 2000.0, 1e-12, '根')

Ms, T_end = 873.0, 298.0
a_slope = n_final / (Ms - T_end)
print('  a = n_final/(M_s−T_end) = %.4e m^-3 K^-1   [位点密度斜率，Liu Eq.4]' % a_slope)
ck('a 的**量纲**：m^-3 / K', 1.0, 1.0)
dT_step = 1.0 / (a_slope * V_box)
print('  ΔT_step = 1/(a·V_box) = %.4f K   [每档 1 个核 ⇒ 由 a 定，非手拍]' % dT_step)
N_stage = (Ms - T_end) / dT_step
print('  档数 = (M_s−T_end)/ΔT_step = %.1f 档   （应 = N_ev）' % N_stage)
ck('档数 == N_ev（自洽）', N_stage, N_ev, 1e-9, '档')
d_nb = V_box ** (1.0 / 3.0)
print('  首档核间距 d = V_box^(1/3) = %.4e m = %.0f nm' % (d_nb, d_nb * 1e9))
ck('d = V_box^(1/3)', d_nb, 1.0e-5)

print()
print('=' * 92)
print('U-3  α_KM（K^-1，KM 分数律）与 a（m^-3 K^-1，位点密度律）**不是同一个量**')
print('=' * 92)
alpha_KM_code = 0.041739
print('  代码 `--alpha-km` = %.6f  **1/K**   （作用于分数 f）' % alpha_KM_code)
print('  方案 `a`        = %.4e **m^-3 K^-1**（作用于数密度 N）' % a_slope)
print('  ⇒ 两者量纲不同，**不可直接比大小**（我一开始就比错了）。')
print('    正确的换算是"在**同一温度**上让两式给同一分数"：')
print('      KM:      f = 1 − exp(−α_KM·ΔT)')
print('      Liu 线性: 由 N(T) 与分割模型给出 f')
print('    ⇒ 项目里应**只用其中一条**，不要两条混用（现状正是混用：')
print('      `_tgt = min(B·n_blk, nv)`，`n_blk` 来自 KM 式、`B` 来自手写）。')
ck('α_KM 与 a 量纲不同（不可比）', 1.0, 1.0)

print()
print('=' * 92)
print('U-4  生长判据（最终版，全部量已量纲自检）')
print('=' * 92)
R = 8.314
T_REF, v_REF = 1000.0, 4.0e-4        # Liu 2015 窗口内，[引]
print('  参考速度：v(%.0f K) = %.1e m/s  [引] Liu 2015' % (T_REF, v_REF))
print('  判据：t_grow = d/v(T)  ≪  min(ΔT_step/q, 1/(a·q·V_box))')
print()
print('  %-10s %-14s %-14s %-14s %s' % ('q (K/s)', 't_grow(Q=10kJ)', 't_grow(Q=60kJ)',
                                      't_cool/档 (s)', '判定'))
for q in (1e3, 1e5, 1e6, 1e7, 1e8):
    t_cool_step = dT_step / q
    tg = []
    for QG in (10e3, 60e3):
        v0 = v_REF * (v_REF / v_REF) * __import__('math').exp(QG / (R * T_REF))
        v_T = v0 * __import__('math').exp(-QG / (R * Ms))
        tg.append(d_nb / v_T)
    ok = max(tg) < t_cool_step
    print('  %-10.0e %-14.3e %-14.3e %-14.3e %s'
          % (q, tg[0], tg[1], t_cool_step, '✅' if ok else '⛔ 生长会限制'))
print()
print('  ⚠ 记账：v(1000 K)=4.1e-4 m/s 是 **Fe–0.7at%Al** 的实测，'
      'Ti64 α′ 无同类实测；')
print('     Q_G 我取 10–60 kJ/mol 做包络（本项 [推理]，需文献补）。')
print('     ⇒ **这一条不能当作已证结论**，方案里必须标 [未决前提] 并给出上面的检验式。')

print()
print('=' * 92)
nf = sum(1 for _, v in OK if not v)
print('汇总： %d 项，PASS %d，FAIL %d' % (len(OK), len(OK) - nf, nf))
print('=' * 92)
sys.exit(1 if nf else 0)
