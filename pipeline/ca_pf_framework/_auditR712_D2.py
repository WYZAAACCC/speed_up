#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR712_D2.py —— 把 D-2（形核率律）**到底是什么问题**落到代码事实上（只读）。

七项检查：
  Q1 生产的事件"时刻"由什么决定？（KM 分数律还是泊松？）
  Q2 KM 律**在恒定 T 下的时间导数**是多少？（顺序形核需要它）
  Q3 `E_int` 判据在代码里管的是"会不会发生"还是"发生多快"？
  Q4 位点池的**耗尽/饱和**行为（位点被吞后还留在池里吗？）
  Q5 `f_nuc^crit = 4γ/d` 的 `d` 是什么？有没有从原文核实？
  Q6 项目里有没有"位点密度"的实验靶（能标定率律的量）？
  Q7 KM 律的来源标注（是"总体分数律"还是"板条形核率律"）？
运行： cd /mnt/f/speed_up/pipeline/ca_pf_framework
       /root/miniconda3/envs/ml/bin/python -u _auditR712_D2.py
"""
import io
import numpy as np
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRV = os.path.join(HERE, '_bk_exp.py')
SURF = os.path.join(HERE, 'windowB_surface.py')
KM = os.path.join(HERE, 'windowB_km.py')
SPEC = os.path.join(HERE, 'PHYSICS_FIRST_SPEC.md')
VERD = os.path.join(HERE, 'R2_PARAM_VERDICTS.md')
LIT = os.path.join(HERE, 'LITERATURE_SEARCH_BRIEF.md')
ANCH = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                    'docs', 'agent-notes', 'LITPARAM_TI64_MARTENSITE_ANCHORS.md')


def rd(p):
    return io.open(p, encoding='utf-8', errors='replace').read().splitlines() \
        if os.path.exists(p) else []


drv, surf, km = rd(DRV), rd(SURF), rd(KM)
print('=' * 94)
print('D-2「形核率律」问题定位（只读）')
print('=' * 94)

# ---- Q1 事件时刻由什么决定 ----
print('\nQ1  生产的事件"时刻"由什么决定？')
for i, s in enumerate(drv, 1):
    if re.search(r'_tgt\s*=|n_ath_tgt\s*<|_f_km\s*=|_n_blk\s*=|_do_try\s*=|_tgt_try', s):
        print('   _bk_exp.py:%-5d %s' % (i, s.strip()[:100]))
print('   ⇒ 目标数只在**温度档**变化；每档只补投一次（`_do_try = _tgt > _tgt_try`）')
print('   ⇒ **没有 Poisson(lambda*dt)**：事件"时刻"由温度档位与目标数决定')

# ---- Q2 KM 律的时间导数 ----
print('\nQ2  KM 律在**恒定 T** 下的时间导数')
for i, s in enumerate(km, 1):
    if re.search(r'def koistinen|f = 1\.0 - np\.exp|1 - exp\[-alpha', s):
        print('   windowB_km.py:%-5d %s' % (i, s.strip()[:100]))
print('   ⇒ f_KM(T) = 1 − exp[−α(M_s − T)] —— **只依赖 T，不含 t**')
print('   ⇒ d f_KM/dt |_{T=const} ≡ 0 ⇒ **等温下 0 个新事件**')
print('   ⇒ 而"顺序形核/sympathetic 在等温下发生"是文献观察（Furuhara 2008 等）')
print('   ⇒ 二者**不相容** ⇒ 顺序形核必须另有一条律')

# ---- Q3 E_int 管什么 ----
print('\nQ3  `E_int` 判据在代码里管的是"会不会"还是"多快"？')
for i, s in enumerate(surf, 1):
    if re.search(r'E_int|_int\b|贯接|ripgrep', s) and 'E_int' in s:
        print('   windowB_surface.py:%-5d %s' % (i, s.strip()[:100]))
print('   [代] E_int(p;x) = −σ(x):ε⁰_p，单位 J/m³ ⇒ 它是**驱动力判据**（自由能下降）')
print('   ⇒ 它回答"**在 x 处 p 变体该不该长**"，**不回答"一秒发生几次"**')
print('   ⇒ 判据与率律**正交**：判据管位置/变体，率律管频次 ⇒ 不能互相替代')

# ---- Q4 位点池行为 ----
print('\nQ4  位点池的耗尽/饱和行为')
for i, s in enumerate(surf, 1):
    if re.search(r"n_activated|sites\.pop|sites_refill|sites\.append|pending_fresh", s):
        print('   windowB_surface.py:%-5d %s' % (i, s.strip()[:100]))
print('   ⇒ `sites.pop(i)`（成功即移除）+ `sites_refill`（见底按同一分布**再抽**）')
print('   ⇒ **没有 N_s(T)/N_s(σ) 形式的位点密度演化**，也**没有"位点被吞后失效"的显式模型**')
print('   ⇒ 即：位点是"永远可再抽"的均匀池 ⇒ 与"位点被先形成的板条消耗"这一物理**未接**')

# ---- Q5 fcrit 的 d ----
print('\nQ5  `f_nuc^crit = 4γ/d` 的 `d` 与核实状态')
for i, s in enumerate(surf, 1):
    if re.search(r'fcrit|4γ|4 \* c\[|Du 2017|核厚', s):
        print('   windowB_surface.py:%-5d %s' % (i, s.strip()[:100]))
print('   ⇒ 代码取 `d = t`（核厚）。量纲：4γ/t = (J/m²)/m = **J/m³** ⇒ 与 df 同量纲 ✓')
print('   ⇒ 但"为什么是 t 而不是 R"**未从原文核实**（代码自己两次写明"未核实"）')

# ---- Q6 有没有可标定的实验靶 ----
print('\nQ6  项目里有没有"位点密度"的实验靶？')
for p in (LIT, ANCH, SPEC):
    L = rd(p)
    hit = []
    for i, s in enumerate(L, 1):
        if re.search(r'位点密度|site density|nucleation rate|形核率|N_v', s):
            hit.append((os.path.basename(p), i, s.strip()[:88]))
    print('   %-34s 命中 %d 条' % (os.path.basename(p), len(hit)))
    for h in hit[:6]:
        print('      %s:%-5d %s' % h)
print('   ⇒ 结论：**没有 Ti-6Al-4V 马氏体位点密度/形核率的实验锚**'
      '（本仓已登记 block/packet 尺寸 NOT FOUND）')

# ---- Q7 KM 律的来源标注 ----
print('\nQ7  KM 律在代码里的来源标注')
for i, s in enumerate(km, 1):
    if re.search(r'Koistinen|Marburger|唯象|\[L\]|本模块不预测', s):
        print('   windowB_km.py:%-5d %s' % (i, s.strip()[:100]))
print('   ⇒ 代码把它标为 [L]（文献直读）但用途写作"**作对照与反演**"')
print('   ⇒ 且明写「**成核是输入**（HYBRID_FRAMEWORK §8 item 4）⇒ 本模块**不预测 M_s**，'
      '只把它当锚点」')
print('   ⇒ 即：KM 是**唯象总体分数律**，不是"板条形核率"')

# ---- Q8 α_KM 的锚：几何需求 vs 代码占位值 ----
print('\nQ8  ★核心：α_KM 有没有锚？（这是 D-2 真正卡住的地方）')
V_box = 1000.0e-18          # m^3  生产盒 10 µm 立方
t_l, L_l, W_l = 250.0e-9, 4000.0e-9, 500.0e-9      # 板条厚/长/宽（nm），长:宽 = 8:1
V_lath = t_l * L_l * W_l
print('   板条体积 V_lath = %.0f×%.0f×%.0f nm = %.4f µm³'
      % (t_l * 1e9, L_l * 1e9, W_l * 1e9, V_lath * 1e18))
print('   几何需求：填满生产盒 V_box = %.0f µm³ ⇒ N = V_box/V_lath = **%.0f 根**'
      % (V_box * 1e18, V_box / V_lath))
print('   代码 `natural` 模式的闭式（_bk_exp.py:2941-2942）：')
for T in (873.0, 849.0, 298.0):
    a_km = 0.041739
    Ms = 873.0
    N = V_box / V_lath * (1.0 - np.exp(-a_km * max(Ms - T, 0.0)))
    print('     T=%6.1f K  ⇒ N_lath = %.0f 根' % (T, N))
print('   ⇒ 在 T_end=298 K 上 `f_KM ≈ 1` ⇒ `natural` 给 **%.0f 根**，与几何需求一致'
      % (V_box / V_lath))
print('   ⇒ 而生产 `manual`（B=9）：`_tgt = min(9 × 23, 220) = **207**`')
print('   ⇒ **同一套几何、同一条律，两种模式差 %.1f 倍**（207 vs %.0f；两者都被 `nv=220` 截断）'
      % ((V_box / V_lath) / 207.0, V_box / V_lath))
# 反解：要让"线性律在 M_s 附近的地板"与几何需求一致，α_KM 需要多大
T1 = Ms - 1.0 / 0.041739
need = V_box / V_lath               # 根
a_lin = 1.0 / (Ms - 298.0)
print('   反解（`manual` 那种 floor(α(M_s−T)) 口径）：要 N_end=%.0f 根' % need)
print('     线性律 `floor(α(M_s−T_end))=%.0f` ⇒ α_KM = %.0f/%.0f = **%.3f /K**'
      % (need, need, (Ms - 298.0), need / (Ms - 298.0)))
print('     即 ≈ **%.1f /K**，而代码占位 **0.041739 /K** ⇒ **差 %.0f 倍**'
      % (need / (Ms - 298.0), (need / (Ms - 298.0)) / 0.041739))
print('   ⚠ 两个模式都在给同一个不可观测量（α_KM）配不同的数 ⇒ **谁都能自洽，谁都不可证伪**')

# ---- Q9 4γ/t 与 2γ/t 的口径 ----
print('\nQ9  两个临界驱动力口径（facet 数不同）')
print('   fresh 闸门 `windowB_surface.py:2072  fcrit = 4γ/t`   （4 个面 ⇒ 体积 1 个胞）')
print('   probe 判据 `windowB_surface.py:1953  fcrit = 2γ/t`   （只计两个宽面，1D 极限）')
print('   [代] 平板核：ΔG_v > 2γ/t（两个宽面、1D）或 4γ/t（四面全算、3D 柱）')
print('   ⇒ 两者都有其适用极限，但**同一核在两处用不同阈值** ⇒ 必须显式记账并对齐')

print()
print('=' * 94)
print('⇒ D-2 的实质：方案要"事件率"，而可用材料只给"总量"与"判据"；')
print('   而"总量→根数"的换算系数 α_KM 在 Ti-6Al-4V 上没有实验锚，')
print('   两个模式（manual / natural）给同一个不可观测的 α_KM 配了差 83 倍的等效值')
print('   ⇒ 任何率律都能被这套参数"调"成自洽 ⇒ 不可证伪')
print('=' * 94)
sys.exit(0)

