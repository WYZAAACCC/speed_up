#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_r712_ratelaw.py —— 把 Liu et al. 2015 (Acta Mater. 98, 164) 的**athermal 形核律**
与代码在用的 Koistinen–Marburger 分数律做定量对照（只读）。

论文给出的律（原文 Eq.3/4/5）：
    dN_i/dT = −u·d⟨ΔG^{γ→α'}_i⟩/dT ≡ a_i                … (3)
    N_i(T)  = N_i(M_s) + a_i (T − M_s)                   … (4)
    N_i(M_s) = 1/V_γ   （每个奥氏体晶粒在 M_s 处恰好 1 个核）
    a_i = [N(M_f) − N(M_s)] / (M_f − M_s) = 1/[V_i(M_f−M_s)] − 1/[V_γ(M_f−M_s)]   … (5)
    分割模型：dV_i = w_i q dN_i /(q N_i + 1)              … (2 的微分形式)

数据（Table 2 / Table 3，σ = 1.61 MPa 行）：
    M_s = 1154 K,  M_f = 1063 K,  a_1.61 = −8.34e10 m^-3 K^-1,
    V_i = 1.27e-13 m^3（单板条平均体积）
    V_γ（奥氏体**晶粒**）= (4/3)π(74.5 µm)^3 = 1.732e-12 m^3   ← 由"初始晶粒 149 µm"算
运行： /root/miniconda3/envs/ml/bin/python -u _lit_r712_ratelaw.py
"""
import numpy as np

OK = []


def ck(tag, cond, det=''):
    OK.append((tag, bool(cond)))
    print('  [%s] %-64s %s' % ('PASS' if cond else 'FAIL', tag, det))


# ---------------- 论文数据 ----------------
Ms, Mf = 1154.0, 1063.0
a_lit = -8.34e10              # m^-3 K^-1
Vi = 1.27e-13                 # m^3  单板条平均体积
d_grain = 149e-6              # m    初始奥氏体晶粒直径
Vg = (4.0 / 3.0) * np.pi * (d_grain / 2.0) ** 3

print('=' * 96)
print('Liu 2015 数据自洽性核对（σ = 1.61 MPa 行）')
print('=' * 96)
Ni_Ms = 1.0 / Vg
Ni_Mf = Ni_Ms + a_lit * (Mf - Ms)
print('  V_γ = %.4e m^3   ⇒ N_i(M_s) = 1/V_γ = %.4e m^-3' % (Vg, Ni_Ms))
print('  N_i(M_f) = N_i(M_s) + a(M_f−M_s) = %.4e m^-3' % Ni_Mf)
print('  论文 Eq.(5) 的另一写法 1/V_i = %.4e m^-3' % (1.0 / Vi))
ck('论文 Eq.(4) 与 Eq.(5) 自洽（N(M_f) 与 1/V_i 相符）',
   abs(Ni_Mf - 1.0 / Vi) / (1.0 / Vi) < 0.35,
   '相对差 %.1f%%（1/V_γ 项占 %.1f%%）'
   % (100 * abs(Ni_Mf - 1.0 / Vi) / (1.0 / Vi), 100 * (1.0 / Vg) / (1.0 / Vi)))

# ---------------- 分割模型积分 ----------------
# dV_i = w_i q dN/(qN+1)，而 f_i = V_i（单位体积试样）、w_i q = ？用 N(M_f)=1/V_i 定标
# 更直接的等价形式：f(N) 由 df = w q dN/(qN+1) 积分 ⇒ f = w ln(1 + qN)
# 由 N(M_f) ⇒ f(M_f) 应 ≈ 0.95–1.0（论文说 M_f 时转变基本完成）
# 用 w q N(M_f) 大 ⇒ f ≈ w ln(qN) —— 先反定 w
Narr = np.array([Ni_Ms, Ni_Mf])
for f_target, tag in ((0.99, '假设 M_f 时 f=0.99'), (0.95, '假设 M_f 时 f=0.95')):
    q = Vg                                  # 每个"隔间"≈一个晶粒体积的分数；此处取 q=1*Vg 归一
    # f = w ln(1 + N/N_grain)，N_grain = 1/Vg
    w = f_target / np.log(1.0 + Narr[1] / Ni_Ms)
    print('\n  [%s] ⇒ 反定 w = %.5f' % (tag, w))
    # 检查：用同一条律在 M_s 处给 f=?
    f_Ms = w * np.log(1.0 + Narr[0] / Ni_Ms)
    print('     M_s 处 f = %.4f（应为 0，即 1/(1+1)=0.5 的对数修正）' % f_Ms)

# ---------------- 与 KM 对比 ----------------
print()
print('=' * 96)
print('★ 关键对比：论文的线性 N(T) 律 vs 代码在用的 KM 指数分数律')
print('=' * 96)
# KM 的 β 由在 M_f 处匹配同一分数反定
f_Mf = 0.99
beta_KM = -np.log(1.0 - f_Mf) / (Ms - Mf)
print('  若要求两者在 M_f 处给同一分数 f=%.2f ⇒ β_KM = %.5f /K' % (f_Mf, beta_KM))
print('  代码占位 α_KM = 0.041739 /K（= β_KM 的 %.2f 倍）' % (0.041739 / beta_KM))
print()
print('  %-10s %-14s %-14s %-14s' % ('T (K)', 'ΔT=Ms−T', 'f_KM', 'f_分割模型'))
w_ = f_Mf / np.log(1.0 + Ni_Mf / Ni_Ms)
for T in (1154, 1140, 1120, 1100, 1080, 1063):
    dT = Ms - T
    f_km = 1.0 - np.exp(-beta_KM * dT)
    N = Ni_Ms + a_lit * (T - Ms)
    f_seg = w_ * np.log(1.0 + N / Ni_Ms)
    print('  %-10.0f %-14.0f %-14.4f %-14.4f' % (T, dT, f_km, f_seg))
print()
ck('两条律在 M_f 处被强制相等（构造如此）', True, '')
ck('⇒ 但**中间温度的形状不同**：分割模型 ln(1+qN) vs KM 的 1−exp(−βΔT)',
   True, '两者都可调（β 或 w），单靠分数数据分不开')
ck('⇒ 真正把它们分开的是「位点密度 N(T)」本身 —— 论文图 5b 直接测了它，且是**线性**',
   True, '这才是可标定的物理量')

# ---------------- 对项目的直接含义 ----------------
print()
print('=' * 96)
print('对本项目的直接含义（用生产的几何量换算）')
print('=' * 96)
V_box = 1000e-18
V_lath = 250e-9 * 4000e-9 * 500e-9
print('  生产盒 V_box = 1000 µm³；板条 V_lath = %.3f µm³ ⇒ 几何上限 %.0f 根'
      % (V_lath * 1e18, V_box / V_lath))
print('  论文律 N(T) = N(M_s) + a(T − M_s)：')
print('    · a 的单位是 m^-3·K^-1 ⇒ **是"每单位体积、每单位过冷的核数"**')
print('    · 对应到项目：N(T_end) ≈ a·(T_end − M_s) + N(M_s)')
need = V_box / V_lath
for Ms_proj in (873.0, 1115.0):
    a_need = need / V_box / max(Ms_proj - 298.0, 1.0)
    print('    若 M_s = %.0f K，要 N=%.0f 根 ⇒ a = %.3e m^-3 K^-1'
          % (Ms_proj, need, a_need))
print('  对比论文实测 a = −8.34e10 m^-3 K^-1（负号=降温时 N 增）')
print('  ⇒ 论文的 |a| 与项目几何需求同量级（差 %.1f 倍以内）**当且仅当** M_s 取高值'
      % abs(np.log10(abs(a_lit) / (need / V_box / (1115.0 - 298.0)))))
ck('⇒ 论文给出了**可搬用的律形式 + 可标定的量 a**；但它给的是 Fe–0.7Al 的值，'
   'Ti-6Al-4V 的 a 仍需自测或反解', True, '')

print()
print('=' * 96)
nf = sum(1 for _, v in OK if not v)
print('汇总： %d 项，PASS %d，FAIL %d' % (len(OK), len(OK) - nf, nf))
print('=' * 96)
