#!/usr/bin/env python3
"""核对偏析过剩 Γ 的温度依赖（与本仓库 gibbs_physics 的单一参数来源一致）"""
import sys
sys.path.insert(0, '/mnt/f/speed_up/pipeline/gibbs')
import gibbs_physics as gp

H, dG = gp.dH_seg_from_anchor()
print('dH_seg = %.1f J/mol (= %.2f kJ/mol) ; dG_seg(923K) = %.1f J/mol' % (H, H / 1e3, dG))
print('%-8s %14s %12s %10s' % ('T (K)', 'Gamma(mol/m2)', 'at/nm2', 'ML'))
for T in (923.0, 1200.0, 1500.0, 1950.0):
    g = gp.gamma_eq_langmuir(gp.C0, T, H)
    print('%-8.0f %14.4e %12.3f %10.3f' % (
        T, g, g / gp.AT_PER_NM2_TO_MOL_PER_M2, g / gp.GAMMA_MONO))
print('注: GAMMA_MONO = %.4e mol/m2 (= %.1f at/nm2 单层饱和)' % (gp.GAMMA_MONO, gp.GAMMA_MONO_AT))
