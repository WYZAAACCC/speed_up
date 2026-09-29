#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_rsval.py —— R30：把 `windowB_lath` 的 Read–Shockley 常数与 γ_RS(θ) 表打出来，
并打印**闭环配置（M 根板条、ladder 0..ω_max）下块内每一对界面的 θ 与 γ_Σ**。

只读、纯解析，不跑仿真。
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_lath as L                                        # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--M', type=int, default=6)
    ap.add_argument('--omega-max-deg', type=float, default=5.0)
    ap.add_argument('--mode', default='ladder')
    ap.add_argument('--gamma0', type=float, default=0.25)
    a = ap.parse_args()

    print('=' * 74)
    print('Read–Shockley 常数（windowB_lath，全部来自该模块的常量）')
    print('=' * 74)
    print('  E_TI64 = %.4f GPa   NU = %.3f   THETA_M = %.1f deg'
          % (L.E_TI64 / 1e9, L.NU_TI64, L.THETA_M_DEG))
    print('  E_0    = Gb/[4pi(1-nu)] = %.6e J/m^2' % L.E0_TI64)
    print('  gamma_m = E_0*theta_m   = %.6f J/m^2' % L.GAMMA_M_TI64)
    print('\n  theta[deg]   gamma_RS[J/m2]   /gamma_m')
    for th in (0.0, 0.5, 1, 2, 3, 4, 5, 10, 15, 20):
        g = float(L.gamma_rs_deg(th))
        print('   %8.2f      %.6f        %.4f' % (th, g, g / L.GAMMA_M_TI64))
    print('   ⚠ gamma_RS(0) = %.3e ⇒ **同变体且同 ω 的两根板条之间没有晶界能**'
          % float(L.gamma_rs_deg(0.0)))

    M = a.M
    ax = np.array([1.0, 0.0, 0.0])
    om = L.default_omega(M, a.omega_max_deg, axis=ax, mode=a.mode)
    lt = L.LathTable([1] * M, omegas=om, gamma0=a.gamma0, label='R30')
    print('\n' + '=' * 74)
    print('闭环块内界面（M=%d，%s，omega_max=%.2f deg，全部同变体 ⇒ 全是 F3）'
          % (M, a.mode, a.omega_max_deg))
    print('=' * 74)
    print('  逐板条 ω 转角[deg]: %s'
          % np.array2string(np.degrees(np.linalg.norm(om, axis=1)), precision=3))
    print('  %-8s %-12s %-14s %s' % ('对', 'theta[deg]', 'gamma_RS', 'vs gamma0=%.2f'
                                     % a.gamma0))
    for i in range(M):
        for j in range(i + 1, M):
            th = float(np.degrees(lt.theta[i + 1, j + 1]))
            g = float(lt.gtab[i + 1, j + 1])
            print('  %-8s %-12.4f %-14.6f %.4f x'
                  % ('%d-%d' % (i + 1, j + 1), th, g, g / a.gamma0))
    print('\n  ⚠ 同一块内**最高的那一对** θ = %.3f deg ⇒ γ = %.4f（%.3f x γ0）'
          % (np.degrees(lt.theta[1, M]), float(lt.gtab[1, M]),
             float(lt.gtab[1, M]) / a.gamma0))
    print('  ⚠ F1（板条/母相）与 F2（不同变体）**都不用 gtab** ⇒ 一律 gamma0 = %.3f'
          % a.gamma0)


if __name__ == '__main__':
    main()
