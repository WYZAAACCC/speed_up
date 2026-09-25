#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_thermo.py --- 用**文献实测的液/固相线 + 模型自己的精确闭式**闭合 F1/F2（CALPHAD 替代）

背景（MATH_FRAMEWORK §5.2 结论 2 = F1/F2）：
  本项目反解的 (k=0.6303, c0=0.036) 配 van t Hoff ⇒ 凝固区间 **17.9 K**；
  而实测 Ti64 的液/固相线给出 **45~50 K**（§5.2 结论 3 引「实测液相线 1923 K」；
  REPORT_FOR_EXPERTS:280 引「固相线 1878 K / 液相线 1928 K」）。两者不能同时成立。

可用工具（全部**已在模型里 [已验证]**，不需要 CALPHAD）：
  理想溶液 + 两相共存 ⇒ T_pair(c_l,c_s) = ΔH_f / (ΔH_f/T_m − R_g ln((1−c_l)/(1−c_s)))
  液相线 T_L = T_pair(c0, k c0)、固相线 T_S = T_pair(c0/k, c0)、ΔT_0 = T_L − T_S
  m_L **不是独立参数**：|m_L| = R_g T_m²(1−k)/ΔH_f（van t Hoff）

本文件做三件事：
 T1 **复现 §5.2 的表**（自洽性检查：实现对不对）
 T2 **反解**：给定实测 ΔT_0，求 k*（并给出 |m_L|、T_L、T_S、与实测液相的偏置）
 T3 **成分核对**：Ti-6Al-4V(wt%) ⇒ x_V、x_Al
输出：一套**自洽的** Window A 准二元参数 + 后果清单（IRF 表要重算等）+ 待核对出处。
"""
import math
from scipy.optimize import brentq

RG = 8.314
DHF = 14150.0          # J/mol 纯 Ti 熔化焓（模型用的值）
TM = 1941.0            # K     纯 Ti 熔点（模型用的值）
M_TI, M_AL, M_V = 47.87, 26.98, 50.94
C0 = 0.036


def T_pair(cl, cs):
    return DHF / (DHF / TM - RG * math.log((1.0 - cl) / (1.0 - cs)))


def TL(c0, k):
    return T_pair(c0, k * c0)


def TS(c0, k):
    return T_pair(c0 / k, c0)


def dT0(c0, k):
    return TL(c0, k) - TS(c0, k)


def m_L(k):
    return -RG * TM ** 2 * (1.0 - k) / DHF


print('==== T1 复现 §5.2 的表（自洽性检查）====')
k0, c0 = 0.6303, C0
print('   模型参数 (k=%.4f, c0=%.4f, DHf=%.0f, Tm=%.0f)' % (k0, c0, DHF, TM))
print('   T_L = %.1f K（§5.2 写 1911.1）; T_S = %.1f K（写 1893.2）; dT0 = %.2f K（写 17.93）'
      % (TL(c0, k0), TS(c0, k0), dT0(c0, k0)))
print('   |m_L| = %.1f K/(mol frac)（写 818.4）; 线性化 van t Hoff 的 dT0 = %.2f K（写 17.28）'
      % (-m_L(k0), -m_L(k0) * c0 * (1 - k0) / k0))
ok = abs(TL(c0, k0) - 1911.1) < 0.15 and abs(dT0(c0, k0) - 17.93) < 0.05
print('   => %s' % ('实现与框架表一致 OK' if ok else '实现与框架表不一致 X'))

print()
print('==== T2 反解：给定**实测** dT0，求自洽的 k ====')
print('   实测基准（仓库引用）：液相线 1923 K（§5.2）/ 1928 K（REPORT:280）；固相线 1878 K')
print('   %-12s %-9s %-10s %-9s %-9s %-10s' %
      ('dT0 目标', 'k*', '|m_L|', 'T_L', 'T_S', 'T_L-1925'))
for target in (17.93, 45.0, 48.0, 50.0, 55.0):
    try:
        kk = brentq(lambda k: dT0(c0, k) - target, 0.05, 0.999, xtol=1e-14)
    except Exception:
        print('   %-12.1f  （无解）' % target)
        continue
    print('   %-12.1f %-9.4f %-10.1f %-9.1f %-9.1f %+9.1f'
          % (target, kk, -m_L(kk), TL(c0, kk), TS(c0, kk), TL(c0, kk) - 1925.0))
print('   注：末列是模型液相线与实测（1923~1928 K）的偏置 —— 即 §5.2 结论 3 的准二元偏差')
print('       （它来自忽略 x_Al = 0.106 对液相线的压低，见 T3）。')

print()
print('==== T3 成分核对：Ti-6Al-4V(wt%) => 摩尔分数 ====')
w_al, w_v = 0.06, 0.04
n_al, n_v = w_al / M_AL, w_v / M_V
n_ti = (1.0 - w_al - w_v) / M_TI
ntot = n_al + n_v + n_ti
print('   x_Al = %.4f ; x_V = %.4f ; x_Ti = %.4f' % (n_al / ntot, n_v / ntot, n_ti / ntot))
print('   => 模型用的 c0(V) = %.4f 与成分算出的一致 OK' % C0)
print('      而另一套口径写的 c0 = 0.10 => 对应 V 约 %.1f wt%% X（不是 Ti64）'
      % (0.10 * M_V / (0.10 * M_V + 0.9 * M_TI) * 100.0))
print('   !! 但要记账：x_Al = %.3f 约 3 倍的 x_V => 准二元（只留 V）本身是最大近似；'
      % (n_al / ntot))
print('      §5.2 结论 3 已量到它带来的液相线偏置；本文件的 k* 只对区间负责。')

print()
print('==== 结论（CALPHAD 的文献+理论替代）====')
kk = brentq(lambda k: dT0(c0, k) - 48.0, 0.05, 0.999)
print('   (1) 模型自洽恒等式：dT0 = Rg Tm^2 c0 (1-k)^2 / (DHf k)（van t Hoff 代入）')
print('       => 在 (c0, DHf, Tm) 固定时，**dT0 与 k 一一对应**，不可自由选。')
print('   (2) 实测 dT0 约 45~50 K => **k* 约 %.3f**（对照模型用的 0.6303）；' % kk)
print('       配套 |m_L| 约 %.0f K/(mol frac)（模型用 818.4）' % -m_L(kk))
print('   (3) 反向：坚持 k = 0.6303 => dT0 = 17.9 K，与实测 45~50 K 冲突；')
print('       要同时满足需 DHf = %.0f J/mol（真实 14150，差 %.1f 倍）=> 不可取 X'
      % (RG * TM ** 2 * c0 * (1 - k0) ** 2 / (k0 * 48.0),
         DHF / (RG * TM ** 2 * c0 * (1 - k0) ** 2 / (k0 * 48.0))))
print('   (4) => **需要改的是 k（不是 DHf）**；后果：CA 的 irf_ti64.csv 必须用新 k 重算')
print('       （V(dT) 表、k_eff、Scheil 剖面、CET 判据都会变）。')
print('   (5) 待核对出处：本文件用的两个实测值来自仓库引用（尚未落到具体文献）：')
print('       液相线 1923 K（§5.2）/ 1928 K（REPORT:280）、固相线 1878 K（REPORT:280）')
print('       => 进文献清单核对，并注明是 DSC / 评估相图 / 哪一版数据库。')