#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_d7.py --- D7 结案自检：CALPHAD 锚点是否自洽，以及它对模型工作点的影响。"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_km as K                                          # noqa: E402

print('=' * 92)
print('_chk_d7 —— D7（CALPHAD 锚点）自检')
print('=' * 92)
ok = K.selftest(verbose=True)
print('-' * 92)
print('文献锚点：T0=%.1f K  Ms=%.1f K  dG(Ms)=%.4e J/m3  DS=%.4e J/(m3 K)'
      % (K.T0_TI64, K.M_S_TI64, K.DG_CRIT_REF, K.DS_REF))
T0, Ms, dGc = K.T_G_from_calphad()
print('  ⇒ `T_G_from_calphad()` 自洽性断言通过：T0_from_Ms(Ms,dGc,DS) = %.3f K' % T0)
print('  ⇒ 单位换算复算：1200 J/mol ÷ 1.064e-5 m3/mol = %.4e J/m3（文献 %.4e）'
      % (1200.0 / 1.064e-5, dGc))
print('-' * 92)
print('对模型工作点的影响（`drive_of_T(T)` = J/m3）：')
for T in (298.0, 400.0, 500.0, 600.0, 663.0, 700.0, 800.0, Ms, 1000.0, T0):
    print('   T = %6.1f K ⇒ 驱动力 = %+.4e J/m3  (= %+.3f ×1e8)'
          % (T, K.drive_of_T(T, T0, K.DS_REF), K.drive_of_T(T, T0, K.DS_REF) / 1e8))
print('-' * 92)
print('旧/新对照：')
print('   %-22s %-14s %-14s' % ('量', 'D7 之前（假设）', 'D7 之后（文献）'))
rows = [('Ms (K)', '848.0', '%.1f' % K.M_S_TI64),
        ('T0 (K)', '1181.3（导出）', '%.1f（文献）' % K.T0_TI64),
        ('dG_crit (J/m3)', '1.000e8（同量级猜）', '%.4e（1200 J/mol）' % K.DG_CRIT_REF),
        ('DS (J/m3K)', '3.000e5（反推）', '%.4e（导出）' % K.DS_REF),
        ('DS 带', '(1.5e5, 6.0e5) = 4×', '(%.2e, %.2e) = ±20%%' % K.DS_BAND)]
for r in rows:
    print('   %-22s %-14s %-14s' % r)
print('-' * 92)
print('工作点反查（★ 用 `T_from_drive`；`T_from_dG` 的入参是 `dG_chem`，符号相反）：')
for df in (1.128e8, 1.5e8, 2.0e8, 3.0e8, 3.512e8):
    Tdf = K.T_from_drive(df, T0, K.DS_REF)
    print('   df = %.4e J/m3  ⇔  T = %.1f K（= %.0f °C）'
          % (df, Tdf, Tdf - 273.15))
print('   ⇒ LPBF 的 α′ 在 Ms(873 K) 以下持续降温中长大；生产用的 df=2e8 对应 **663 K（390 °C）**，')
print('     落在"层间温度 ~200–600 °C"的合理区间内 ⇒ 旧的生产值**没有把 ΔG 设得离谱**。')
print('   ⇒ df=3.512e8 对应 **298 K（室温）** ⇒ 室温下的驱动力是生产值的 **1.76 倍**。')
print('-' * 92)
print('★ T8 的分界冷速 `q*` 需要用**新常数**重算（旧值 2.4e7 K/s 是在 DS=3.0e5 下算的）：')
for L_m in (4.0e-6,):
    for df in (1.128e8, 2.0e8):
        qs = K.M_S_TI64 and (K.MOB_REF_PROXY if hasattr(K, 'MOB_REF_PROXY') else 1e-9) * df / L_m
        print('   df=%.3e:  q* = M·df/L = %.3e K/s（用 M=1e-9 m4/(J·s)，L=%.1f µm）'
              % (df, qs, L_m * 1e6))
print('=' * 92)
sys.exit(0 if ok else 1)
