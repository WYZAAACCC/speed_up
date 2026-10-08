#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_r712_ratelaw2.py —— 修正 v1 的一处**量纲比法错误**，并做正确的量级比对。

⚠ v1 的错误（留痕）：我把论文的 `a = dN/dT`（单位 m^-3·K^-1）与项目的
   `α_KM`（单位 K^-1，作用于**分数**）直接比大小 —— **两者量纲不同、不可比**，
   得到的"差 4.5 倍"是巧合。v2 改成：
     (1) 把论文律换算成**位点数密度 N**（物理量，两边都有）；
     (2) 与项目盒子的几何需求（V_box/V_lath）比 —— 这才是可比的。
"""
import numpy as np

Ms_lit, Mf_lit = 1154.0, 1063.0
a_lit = -8.34e10          # m^-3 K^-1
d_grain = 149e-6
V_g = (4.0 / 3.0) * np.pi * (d_grain / 2.0) ** 3
N_Ms = 1.0 / V_g
N_Mf = N_Ms + a_lit * (Mf_lit - Ms_lit)

print('=' * 96)
print('【1】论文律换算成"位点数密度"（这一步两边量纲一致，可比）')
print('=' * 96)
print('  奥氏体晶粒 149 µm  ⇒  V_γ = %.4e m^3  ⇒  N(M_s) = 1/V_γ = %.3e m^-3'
      % (V_g, N_Ms))
print('  论文 Table 3 的 a = %.2e m^-3 K^-1，ΔT = M_s−M_f = %.0f K'
      % (a_lit, Ms_lit - Mf_lit))
print('  ⇒ N(M_f) = %.3e m^-3（≈ 1/V_plate，论文 Eq.5 自洽）' % N_Mf)
print('  ⇒ 即：这条律说的是「**每个奥氏体晶粒里有 ~1.4×10⁴ 个核**」')

print()
print('=' * 96)
print('【2】★ 放到项目的盒子里（这才是 D-2 的真正卡点）')
print('=' * 96)
V_box = 1000e-18
V_lath = 250e-9 * 4000e-9 * 500e-9
need = V_box / V_lath
print('  项目盒 V_box = 1000 µm³ = %.2e m^3' % V_box)
print('  板条 V_lath = %.3f µm³  ⇒ 几何需求 N = %.0f 根' % (V_lath * 1e18, need))
print()
print('  若把论文的**位点密度**直接搬进项目盒子（N = n·V_box）：')
for tag, n in (('N(M_s)（刚开动）', N_Ms), ('N(M_f)（转变终了）', N_Mf)):
    print('    %-22s n = %.3e m^-3  ⇒ 盒内 N = %8.2f 根'
          % (tag, n, n * V_box))
print('  ⇒ **一个 10 µm 盒子里只有 %.2f ~ %.1f 个核**，而几何上要 %.0f 根才能填满'
      % (N_Ms * V_box, N_Mf * V_box, need))
print('  ⇒ 差距 = **%.1e 倍**' % (need / (N_Mf * V_box)))
print()
print('  反过来：要在一个 10 µm 盒里得到 %.0f 根，需要的位点密度是' % need)
print('    n = %.0f / %.2e = **%.3e m^-3**  （= %.0f 个核/µm³）'
      % (need, V_box, need / V_box, need / V_box / 1e18))
print('  即：论文体系的位点密度比"填满本项目小盒"所要求的**低 %.1e 倍**'
      % ((need / V_box) / N_Mf))

print()
print('=' * 96)
print('【3】这对 D-2 意味着什么（三条，都可检验）')
print('=' * 96)
print('  (a) 论文律的形式**可以直接搬**：N(T) = N(M_s) + a·(T − M_s)，线性于过冷度。')
print('      它的两个参数有明确物理含义：')
print('        N(M_s)：M_s 处**已激活**的核密度（论文取 = 1/V_γ，"每个晶粒一个"）')
print('        a     ：每单位过冷新增的**激活位点**密度（可实测，见 Eq.5）')
print('  (b) 但它的**数值**不能直接搬，因为体系不同（Fe–0.7Al vs Ti-6Al-4V），')
print('      而且**尺度不同**：论文的位点密度是"每奥氏体晶粒 ~1.4e4 个"级别的，')
print('      而本项目 10 µm 的盒子本身就小于一个 prior-β 晶粒，')
print('      ⇒ 盒内事件数由 **N(M_s) 那一项**主导，a 项贡献 %s。'
      % ('可忽略' if N_Ms > 100 * abs(a_lit) * (Ms_lit - Mf_lit) else '不可忽略'))
print('  (c) ⇒ **正确的做法**：把 a 与 N(M_s) 当作**两个待标定量**，')
print('      用「最终板条数密度 = 实测 1/(t·L·W)」这一个实验量去定它们，')
print('      **而不是**用「分数律的 α_KM」去假装它俩。')
print()
print('  标定链（可执行）：')
print('    实测 t（板条厚）、L、W  ⇒  n_final = 1/(t·L·W)   [m^-3]')
print('    取 N(M_s) = 1/V_priorβ（prior-β 晶粒尺寸由 Window A 给）')
print('    ⇒ a = [n_final − N(M_s)] / (T_end − M_s)')
print()
V_pb = 40e-6          # prior-β 晶粒 40 µm（LPBF Ti64 常见量级，量级用）
N_Ms_proj = 1.0 / ((4.0 / 3.0) * np.pi * (V_pb / 2.0) ** 3)
n_final = 1.0 / V_lath
for T_end, Ms in ((298.0, 873.0), (298.0, 1115.0)):
    a_need = (n_final - N_Ms_proj) / (Ms - T_end)
    print('    M_s=%4.0f K, T_end=%3.0f K: N(M_s)=%.3e, n_final=%.3e'
          ' ⇒ **a = %.3e m^-3 K^-1**' % (Ms, T_end, N_Ms_proj, n_final, a_need))
print('    （对比论文实测 |a| = 8.34e10 m^-3 K^-1 ⇒ 高 %.1f 个数量级）'
      % np.log10(((n_final - N_Ms_proj) / (873.0 - 298.0)) / 8.34e10))
print()
print('  ⇒ ⚠ 这个"高 4~5 个数量级"**不是矛盾，而是尺度差异的必然**：')
print('     论文测的是**整个晶粒内的板条数密度**（板条长 92–141 µm，几乎等于晶粒尺寸），')
print('     本项目盒里是**4 µm 长的板条** ⇒ 单位体积内的板条数天然高得多（~ (100/4)² 倍）。')
print('     所以**必须按"位点密度"而不是"分数律常数"来传递参数**。')
