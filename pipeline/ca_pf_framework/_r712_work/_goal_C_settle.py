#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_goal_C_settle.py —— C 的定量结算：`M_s` 的不确定度如何传播到 `a`（只读）。

来源（全部逐字读到）：
  · Ji 2016（s11669-015-0436-9.pdf）
      :587  "Assuming Ms = 873 K (600 °C), then this critical driving force
             can be estimated to be 1200 J/mol"
      :579  "martensite start transformation temperature (Ms) (around 550–650 °C)"
  · Heating-induced-martensitic-transformation 2014:35
      "(Ms) significantly (−160 K/at.% O)"      ← 氧**降低** Ms（原文如此）
运行： /root/miniconda3/envs/ml/bin/python -u _goal_C_settle.py
"""
import numpy as np

DSC = 4.147e5      # J/(m^3 K)  = DG_CRIT/|T0-Ms|，代码 windowB_km.py:98
DG_CRIT = 1.128e8  # J/m^3      临界驱动力幅值（1200 J/mol ÷ V_m）
V_lath = 250e-9 * 4000e-9 * 500e-9      # m^3 生产板条
V_box = 1000e-18                        # m^3 生产盒
n_final = 1.0 / V_lath                  # m^-3 目标位点数密度
T_end = 298.0

print('=' * 92)
print('C-1  M_s 的候选与来源（逐字）')
print('=' * 92)
cands = [
    ('代码现用', 873.0, 'windowB_km.py:93 M_S_TI64 = 873.0，标 [L] Ji 2016'),
    ('Ji 原文语境下限', 823.0, 'Ji :579「around 550–650 °C」= 823–923 K'),
    ('Ji 原文语境上限', 923.0, '同上'),
    ('LITPARAM 的片段值', 1115.0, '842 °C；该文件自标"与常见值冲突、置信度中"'),
]
for tag, v, src in cands:
    print('  %-18s M_s = %7.1f K  ← %s' % (tag, v, src))
print()
print('  ★ Ji 原文用词是 "**Assuming** Ms = 873 K" ⇒ 它是**为估 ΔG 而取的名义值**，')
print('    不是该文测量的 M_s。而该文自己给出的实测语境是 **823–923 K**。')

print()
print('=' * 92)
print('C-2  自洽性检验：若改 M_s，必须同时改 η/ΔG 才算自洽')
print('=' * 92)
T0 = 1145.0
for Ms in (823.0, 873.0, 923.0, 1115.0):
    # 保持"DS = DG_CRIT/(T0-Ms)"这条导出关系 ⇒ 给定 DS 反解 T0
    T0_need = Ms + DG_CRIT / DSC
    ok = abs(T0_need - T0) < 3.0
    print('  M_s=%7.1f ⇒ 要保持 DS=%.3e 不变，需 T0 = %7.1f K '
          '（文献 T0=1145.0）%s' % (Ms, DSC, T0_need, '✅ 自洽' if ok else '⛔ 不自洽'))
print('  ⇒ [推理] 873 K 与 (T0=1145, DS=4.147e5) **是同一组自洽三元组**（差 %.1f K）；'
      % abs((873.0 + DG_CRIT / DSC) - T0))
print('     而 823/923/1115 K 若只改 M_s 不改 T0 或 DS，会破坏 windowB_km.T_G_from_calphad() 的断言。')

print()
print('=' * 92)
print('C-3  ★ M_s 的不确定度 → 标定常数 a 的不确定度（这是要报给方案的数）')
print('=' * 92)
N_Ms_grain = 1.0 / ((4.0 / 3.0) * np.pi * (40e-6 / 2.0) ** 3)   # prior-β 40 µm
print('  a = [n_final − N(M_s)] / (T_end − M_s)')
print('    n_final = 1/(t·L·W) = %.4e m^-3   （t=250 nm, L=4 µm, W=500 nm）' % n_final)
print('    N(M_s)  = 1/V_priorβ = %.4e m^-3 （prior-β 40 µm；仅占 n_final 的 %.2e）'
      % (N_Ms_grain, N_Ms_grain / n_final))
print()
print('  %-10s %-14s %-16s %-14s' % ('M_s (K)', 'ΔT=T_end−M_s', 'a (m^-3 K^-1)', '相对 873 K'))
base = None
for Ms in (823.0, 848.0, 873.0, 923.0, 1115.0):
    a = (n_final - N_Ms_grain) / (Ms - T_end)
    if abs(Ms - 873.0) < 1e-9:
        base = a
    print('  %-10.0f %-14.0f %-16.4e %-14s'
          % (Ms, Ms - T_end, a, '—' if base is None else '%.2f×' % (a / base)))
print()
print('  ⇒ **M_s 在 Ji 的实测语境带 823–923 K 内变动 ⇒ a 变动 %.0f%%**'
      % (100 * abs(((n_final - N_Ms_grain) / (823.0 - T_end))
                   / ((n_final - N_Ms_grain) / (923.0 - T_end)) - 1)))
print('  ⇒ 若误用 1115 K，a 会被低估 **%.0f%%**（因为 ΔT 被放大）'
      % (100 * (1 - ((n_final - N_Ms_grain) / (1115.0 - T_end)) / base)))
print()
print('  ★★ 但更关键的一条：**N(M_s) 项可以忽略**（占 %.1e）⇒ ' % (N_Ms_grain / n_final))
print('     a ≈ n_final/(T_end − M_s)，即"**标定常数只由目标板条数密度与 ΔT 定**"。')
print('     物理含义：在比 prior-β 晶粒**小**的盒子里，晶界起始位点密度本就是 0，')
print('     所有核都来自"体相的、与过冷度成正比的位点"这一项。')

print()
print('=' * 92)
print('C-4  结论与建议（写进方案用）')
print('=' * 92)
print('  1) M_s 取 **873 K** 是**可辩护**的：它与 (T0=1145 K, DS=4.147e5) 构成')
print('     自洽三元组（Ji 2016 的 CALPHAD 锚，代码有断言守着）。')
print('  2) 但必须**同时报不确定带** M_s ∈ [823, 923] K（Ji 自己的实测语境），')
print('     ⇒ a 的不确定度 **±%.0f%%**（不是数量级）。' % (100 * 0.5 * (
      ((n_final - N_Ms_grain) / (823.0 - T_end)) / base
      - ((n_final - N_Ms_grain) / (923.0 - T_end)) / base)))
print('  3) **1115 K 不可用**：它既不在 Ji 的语境带内，也会把 a 低估 %.0f%%。' % (
      100 * (1 - ((n_final - N_Ms_grain) / (1115.0 - T_end)) / base)))
print('  4) 若将来拿到更可靠的 M_s，**必须同时重定 DS 或 T0**，否则')
print('     `windowB_km.T_G_from_calphad()` 的自洽断言会失败（这是设计如此）。')
