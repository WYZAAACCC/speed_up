#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_ab_irf.py <irf_csv> <t_end> <tag> --- Window A 的 IRF 敏感度 A/B（同种子/同热场/同 dx，只换表）

设定完全沿用 demo_ca3d_meltpool.py（静态熔池 + 底面 8x8 外延形核 + dx=2um），
只把 IRF 表换成给定路径 ⇒ 隔离"IRF(ΔT) 选择"对晶粒结构的影响。
"""
import os
import sys
import time
import numpy as np
from ca3d import CA3D, IRF, T_LIQ, T_SOL, C0_V, K_V, M_L


def run(irf_path, t_end, tag, tau=3.1e-4, nuc=8):
    dx = 2.0e-6
    nx, ny, nz = 48, 48, 36
    irf = IRF(irf_path)
    ca = CA3D(nx, ny, nz, dx, irf=irf, seed=2026)
    ng0 = ca.nucleate_substrate_grid(nuc, nuc)
    T_peak, sigma, T_bath = 2500.0, 25e-6, 353.0
    T_init = ca.T_meltpool(T_peak, sigma, tau, T_bath)
    ca.seed_solid_from_substrate(T_init, T_SOL)
    V_max = max(float(irf(np.array([max(T_LIQ - T_SOL, irf.dT_lo)]))[0]), 0.2)
    dt = dx / (4.0 * V_max)
    nst = int(t_end / dt)
    t0 = time.time()
    for s in range(nst):
        ca.t = s * dt
        T = ca.T_meltpool(T_peak, sigma, tau, T_bath)
        ca.step(dt, T, window=None)
    ca.scheil_chemistry()
    fs = ca.solid_fraction()
    nlive = len(ca.grain_ids())
    vf = ca.grain_volume_frac()
    arr = np.array(sorted(vf.values(), reverse=True)) if vf else np.zeros(1)
    c = ca.cl[ca.gid > 0]
    ident = ca.check_scheil_conservation()
    nl = max(getattr(ca, "n_front_steps", 1), 1)
    out = dict(tag=tag, dt=dt, nst=nst, sec=time.time() - t0, fs=float(fs),
               nlive=nlive, ngb=ca.gb_area(), top1=float(arr[0]),
               cmax=float(c.max()) if c.size else float('nan'),
               cmed=float(np.median(c)) if c.size else float('nan'),
               dT_lo_pct=100.0 * getattr(ca, "n_dT_low", 0) / nl,
               dT_hi_pct=100.0 * getattr(ca, "n_dT_high", 0) / nl,
               scheil=float(max(abs(t - C0_V) / C0_V for (f, t) in ident)),
               irf_lo=irf.dT_lo, irf_hi=irf.dT_hi)
    return out


if __name__ == '__main__':
    path, t_end, tag = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    tau = float(sys.argv[4]) if len(sys.argv) > 4 else 3.1e-4
    nuc = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    o = run(path, t_end, tag, tau=tau, nuc=nuc)
    print('   tau=%.2e s（热场衰减时间）; 形核网格 %dx%d' % (tau, nuc, nuc))
    print('%s | IRF ΔT ∈ [%.2f, %.2f] K | dt=%.2e nst=%d (%.0f s)'
          % (o['tag'], o['irf_lo'], o['irf_hi'], o['dt'], o['nst'], o['sec']))
    print('   f_s=%.4f  存活晶粒=%d  GB 面积=%.3e m2  top1 体积占比=%.4f'
          % (o['fs'], o['nlive'], o['ngb'], o['top1']))
    print('   c 范围: 中位 %.4f 最大 %.4f (c0=0.036)  Scheil 守恒 %.2e'
          % (o['cmed'], o['cmax'], o['scheil']))
    print('   IRF 越界(前沿固相胞): dT<lo %.3f%% ; dT>hi %.3f%%'
          % (o['dT_lo_pct'], o['dT_hi_pct']))
