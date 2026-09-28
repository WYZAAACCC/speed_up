#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_faces.py --- 独立审计判据：**三个物理面（惯习面 n / 侧面 w / 端面 a）的
真实推进速度**，用「从形心沿固定方向射线找界面」的口径量，完全不依赖 extent/包围盒。

目的：把「M(n) 到底有没有生效」与「形状量测伪影」彻底分开。
  · 种子用**矩形棱柱**（面法向严格 = n_hab / w / a），所以每个面的取向是已知的；
  · 关闭弹性、关闭曲率（gamma=0）、关闭重初始化 ⇒ v = M·df·Mfac 是唯一物理；
  · 逐时记录 r_n / r_w / r_a（射线交点），与理论比 v_n:v_w:v_a = 1:e^-bw:e^-bh 比较。
"""
import os, sys, time
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from windowB_pf3d import C_cubic, _lam_full
from windowB_ti64_variants import variants
import windowB_surface as W

BH, BW = 3.5, 2.3
N, dx = 96, 2e-8
L = N * dx
k = 1

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
eps0, _F, _m = variants()
rng = np.random.default_rng(0)
npref = {}
for v in range(len(eps0)):
    best, bn = None, None
    for n in rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
        if best is None or val < best:
            best, bn = val, n
    npref[v + 1] = bn


def run(noelastic=True, gamma=0.0, nstep=150, pole='box', record=10):
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=gamma, Mob=1e-9,
                        df=[0.0] + [2e8] * len(eps0), workers=4, reinit_every=0)
    if noelastic:
        g.pf = None
    n_h = np.asarray(npref[k], float); n_h /= np.linalg.norm(n_h)
    wv = np.asarray(g.wtab[k], float); wv /= np.linalg.norm(wv)
    av = np.asarray(g.atab[k], float); av /= np.linalg.norm(av)
    # 正交化（矩形棱柱要求三轴正交）：以 n_h 为基准
    wv = wv - (wv @ n_h) * n_h; wv /= np.linalg.norm(wv)
    av = np.cross(n_h, wv); av /= np.linalg.norm(av)
    cen = np.array([L / 2] * 3)
    rel = g.XYZ - cen
    d_n = rel @ n_h; d_w = rel @ wv; d_a = rel @ av
    if pole == 'box':
        sdf = np.maximum(np.maximum(np.abs(d_n) - 1.0e-7, np.abs(d_w) - 1.0e-7),
                         np.abs(d_a) - 2.5e-7)
    else:                                     # 各向同性立方体（正对照）
        sdf = np.maximum(np.maximum(np.abs(d_n), np.abs(d_w)), np.abs(d_a)) - 1.5e-7
    g.phi[k] = np.minimum(g.phi[k], sdf)
    for j in range(g.nreg):
        if j != k:
            g.phi[j] = np.maximum(g.phi[j], -sdf)
    g.init_parent()

    def ray(u):
        """从形心沿 +u / -u 找 phi_k 的第一个变号，线性插值半径（两向取平均）"""
        s = np.arange(0, int(N * 0.49)) * dx
        pts = cen[None, :] + s[:, None] * u[None, :]
        idx = pts / dx - 0.5
        i0 = np.floor(idx).astype(int)
        ok = ((i0 >= 0) & (i0 <= N - 2)).all(1)
        i0 = np.clip(i0, 0, N - 2)
        fr = idx - i0
        f = g.phi[k]
        v = np.zeros(len(s))
        for c in range(8):
            o = np.array([(c >> 0) & 1, (c >> 1) & 1, (c >> 2) & 1])
            wgt = np.prod(np.where(o == 1, fr, 1 - fr), axis=1)
            v += wgt * f[i0[:, 0] + o[0], i0[:, 1] + o[1], i0[:, 2] + o[2]]
        v = np.where(ok, v, np.nan)
        sg = np.where(np.isnan(v[:-1]) | np.isnan(v[1:]), False, v[:-1] * v[1:] < 0)
        ii = np.argmax(sg) if sg.any() else None
        if ii is None or not sg.any():
            return np.nan
        t = v[ii] / (v[ii] - v[ii + 1])
        return (s[ii] + t * dx)

    M = 1e-9
    dt = 0.15 * dx / (M * 2e8)
    vth_ratio = (1.0, np.exp(-BW), np.exp(-BH))
    print('=' * 100)
    print('种子=矩形棱柱  n_hab/2=0.1um  w/2=0.1um  a/2=0.25um ; N=%d dx=%.0fnm L=%.2fum ; noelastic=%s gamma=%.2f'
          % (N, dx * 1e9, L * 1e6, noelastic, gamma))
    print('正交化后: n.w=%.2e  n.a=%.2e  w.a=%.2e (应全 0)'
          % (n_h @ wv, n_h @ av, wv @ av))
    print('Mfac 设计值: n=%.4f  w=%.4f  a=%.4f   =>  v 比 1 : %.3f : %.3f'
          % (np.exp(-BH), np.exp(-BW), np.exp(-3.5 * (av @ n_h) ** 2 - 2.3 * (av @ wv) ** 2),
             np.exp(-BW), np.exp(-BH)))
    print('%-7s %-9s %-22s %-22s %-22s %-9s' % ('step', 'dt(1e-9s)', 'r_n(um)  [增量/步 nm]',
                                                'r_w(um)  [增量/步 nm]', 'r_a(um)  [增量/步 nm]', 'M6p(deg)'))
    t0 = time.time()
    rec = []
    for it in range(1, nstep + 1):
        d = g.advance(dt, aniso=0.4, npref=npref, band_cells=20,
                      mob_beta=BH, mob_beta_w=BW, adv_grad='central')
        ndt = g.suggest_dt(cfl=0.15, dt_prev=dt)
        if ndt:
            dt = ndt
        if it % record == 0 or it == 1:
            r = (ray(n_h), ray(wv), ray(av))
            rec.append((it, dt, r))
            if len(rec) >= 2:
                pi, pdt, pr = rec[-2]
                dn = (r[0] - pr[0]) / (it - pi) * 1e9
                dw = (r[1] - pr[1]) / (it - pi) * 1e9
                da = (r[2] - pr[2]) / (it - pi) * 1e9
                rn = '%.4f [%+.3f]' % (r[0] * 1e6, dn)
                rw = '%.4f [%+.3f]' % (r[1] * 1e6, dw)
                ra = '%.4f [%+.3f]' % (r[2] * 1e6, da)
            else:
                rn, rw, ra = '%.4f' % (r[0] * 1e6), '%.4f' % (r[1] * 1e6), '%.4f' % (r[2] * 1e6)
            print('%-7d %-9.3f %-22s %-22s %-22s' % (it, dt * 1e9, rn, rw, ra), flush=True)
    print('用时 %.0f s' % (time.time() - t0))
    if len(rec) >= 2:
        i0, _, r0 = rec[0]; i1, _, r1 = rec[-1]
        dn = (r1[0] - r0[0]); dw = (r1[1] - r0[1]); da = (r1[2] - r0[2])
        print('=> %d 步累计: Δr_n=%.1f nm  Δr_w=%.1f nm  Δr_a=%.1f nm' %
              (i1 - i0, dn * 1e9, dw * 1e9, da * 1e9))
        print('=> 实测比  n:w:a = %.3f : %.3f : 1.000   （设计 %.3f : %.3f : 1.000）'
              % (dn / da, dw / da, np.exp(-BH), np.exp(-BW)))


if __name__ == '__main__':
    run(noelastic=True, gamma=0.0, nstep=150)
    run(noelastic=False, gamma=0.0, nstep=60)
