#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_rve3d.py --- Window B 的三维板条级 RVE（全 12 个 Burgers 变体）

目的是"能清晰反映板条的形成与变化"（用户决定 1）。参数台账见 WINDOWB_PARAMS.md。

物理内容（本文件不做简化之外的事）:
  * 12 个变体序参量 phi_v + 隐式母相 beta（Σ phi_v <= 1）
  * FFT 微弹性（Khachaturyan，clamped k=0 约定）
  * 双阱 + 梯度（界面能 = gamma，宽度 = w90）
  * 化学驱动 dG（12 个 alpha' 变体成分相同 => dG 相同）
  * 非热马氏体：末态由能量主导（见 WINDOWB_PARAMS.md §4），迁移率只定"多快"

记账（不得省略）:
  - 用 W phi^2 (1-phi)^2 的单阱障碍近似多相场；beta/alpha' 与 alpha'/alpha' 界面用的是
    同一个 gamma（严格做法是成对 W_{vv'} 且两类界面能不同）=> 待精化
  - 各向同性 C；界面宽 w90 = 4*dx 远大于真实的 ~1 nm（由 w 收敛研究兜底）
"""
import os
import sys
import time
import numpy as np
from windowB_pf3d import PF3D, C_iso3
from windowB_ti64_variants import variants

OUT = '/mnt/f/speed_up/bench/windowB_rve3d'


def seed_variants(pf, vol_frac=0.06, rng=0, nblob=2):
    """把 12 个变体各随机种 nblob 个小块（互不重叠；剩余为母相）"""
    N = pf.N
    rg = np.random.default_rng(rng)
    pf.phi[:] = 0.0
    side = max(3, int(round(N * (vol_frac / (pf.nv * nblob)) ** (1 / 3.0))))
    occ = np.zeros((N, N, N), bool)
    for v in range(pf.nv):
        for _ in range(nblob):
            for _try in range(200):
                i = rg.integers(0, N - side)
                j = rg.integers(0, N - side)
                k = rg.integers(0, N - side)
                blk = (slice(i, i + side), slice(j, j + side), slice(k, k + side))
                if not occ[blk].any():
                    occ[blk] = True
                    pf.phi[v][blk] = 1.0
                    break
    return side


def calibrate_L(pf_proto, df, v_target, Nx=48, dx=4e-9, nst=100, dt=2e-11):
    """平面界面标定: 体积分数法测界面速度 => 反解 L 使 v = v_target
       （用 48^3 小盒 + 法向沿 x 的平面界面; 平面速度与盒尺寸无关）"""
    from windowB_pf3d import PF3D as _P
    C = pf_proto.C
    e0 = pf_proto.eps0[:1]
    pf = _P(Nx, Nx * dx, C, e0, gamma=pf_proto.gamma, w90=pf_proto.w90, Lmob=1.0,
            dG=df, workers=1)
    x = (np.arange(Nx) + 0.5) * dx
    a = pf.w90 / 4.394449
    p = 0.5 * (1 - np.tanh((x - 0.25 * Nx * dx) / (2 * a)))
    pf.phi[0] = np.broadcast_to(p[:, None, None], (Nx, Nx, Nx)).copy()
    f0 = pf.phi[0].mean()
    for _ in range(nst):
        pf.step(dt)
    v = (pf.phi[0].mean() - f0) * (Nx * dx) / (nst * dt)     # L=1 时的速度
    return v_target / v, v


def main(N=96, dx=1e-8, nstep=1200, monitor=50, dg_ratio=0.05, v_target=50.0,
         gamma=0.15, w90_over_dx=4.0, workers=8, tag=''):
    os.makedirs(OUT, exist_ok=True)
    L = N * dx
    w90 = w90_over_dx * dx
    # ★ 驱动必须与势垒"按真实比值"配套:
    #   真实界面宽 ~1 nm => W_real = 13.18*gamma/1nm ~ 2e9 J/m^3, 而 Delta f ~ 1e8
    #   => Delta f / W ~ 0.05。若数值上取 W(40nm)=得 5e7 却仍用 Delta f=5e7, 则
    #   界面失稳、区域会变成"多变体混合"（实测 phi_max 从 0.9 掉到 0.5）——那是数值伪影。
    #   故默认按 dG = dg_ratio * W 取值, 并由 S4 敏感度扫描 dg_ratio。
    W = 13.183297 * gamma / w90
    dG = dg_ratio * W
    C = C_iso3(113e9, 0.34)
    eps0, Fs, meta = variants()
    print('=' * 96)
    print('Window B 3D RVE:  N=%d  L=%.3f um  dx=%.1f nm  w90=%.1f nm  12 变体'
          % (N, L * 1e6, dx * 1e9, w90 * 1e9))
    print('  gamma=%.3f J/m^2   W=%.3e J/m^3   kappa=%.3e J/m   dG=%.2e J/m^3'
          % (gamma, 13.183297 * gamma / w90, 1.365472 * gamma * w90, dG))
    print('=' * 96)
    t0 = time.time()
    pf = PF3D(N, L, C, eps0, gamma=gamma, w90=w90, Lmob=1.0, dG=dG, workers=workers)
    print('  Lambda 预计算完成 %.1f s' % (time.time() - t0))
    Lmob, v1 = calibrate_L(pf, dG, v_target)
    pf.Lmob = Lmob
    dt = 0.4 * dx / v_target
    print('  1D 标定: L=1 时 v = %.4e m/s  =>  L = %.4e   (目标 v = %.1f m/s)' % (v1, Lmob, v_target))
    print('  dt = %.3e s ; 计划 %d 步 (物理时间 %.3e s)' % (dt, nstep, dt * nstep))
    side = seed_variants(pf, vol_frac=0.12, rng=7)
    print('  初始种子块 %d^3 胞/块（每变体 2 块）' % side)

    hist = []
    t_start = time.time()
    for s in range(nstep + 1):
        if s % monitor == 0 or s == nstep:
            Eb, Ec, Eg = pf.E_chem_grad()
            Ee = pf.E_el()
            frac = pf.phi.reshape(pf.nv, -1).mean(1)
            hist.append((s, Ee, Eb, Ec, Eg, Ee + Eb + Ec + Eg) + tuple(frac))
            el = time.time() - t_start
            print('  step %5d/%d  E_el=%.4e  E_bar=%.4e  E_chem=%.4e  E_grad=%.3e  E_tot=%.4e'
                  '  | f_parent=%.3f  max_f=%.3f  墙上 %.0fs'
                  % (s, nstep, Ee, Eb, Ec, Eg, Ee + Eb + Ec + Eg,
                     1 - frac.sum(), frac.max(), el), flush=True)
        if s == nstep:
            break
        pf.step(dt)

    np.save(os.path.join(OUT, 'phi_final%s.npy' % tag), pf.phi)
    np.save(os.path.join(OUT, 'hist%s.npy' % tag), np.array(hist))
    print('\n  已保存: %s/phi_final%s.npy 与 hist%s.npy' % (OUT, tag, tag))
    return pf, hist


if __name__ == '__main__':
    kw = {}
    for a in sys.argv[1:]:
        k, v = a.split('=')
        try:
            kw[k] = int(v)
        except ValueError:
            try:
                kw[k] = float(v)
            except ValueError:
                kw[k] = v
    main(**kw)
