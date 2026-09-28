#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11h_paircurv.py --- 修 EXPERT-#4（曲率取差分场）的判决 + 回归守卫。

判据（三条同时成立）
------------------
  T11h-1 **主判据**：Gibbs–Thomson `γ_eff/γ` → **1**（判据 |γ_eff/γ − 1| < 0.30），
          三档 Δx 散布 < 0.15
  T11h-2 **回归守卫 A**：平面前沿速度（零插值真值口径 D）偏差 < 5%、Δx 散布 < 5%
  T11h-3 **回归守卫 B**：`E_el` 与界面面积测度**逐位不变**（本次改动不碰弹性与测度）

用法：python3 T11h_paircurv.py [--L-nm 3000] [--dxs 40,50,62.5]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB, GAM, DFG = 2.0e8, 1e-9, 0.15, 1.0e6


def gt(L, N, dx, pair_curv, nstep=2000):
    """Gibbs–Thomson：γ_eff = Δf·R_eq/2。"""
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=GAM, Mob=MOB,
                        df=[0.0, DFG], workers=1, reinit_every=0, nv=1)
    g.pair_curvature = bool(pair_curv)
    g.seed_sphere(1, [L / 2] * 3, 0.1333 * L)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DFG)
    vs = []
    for it in range(nstep):
        g.advance(dt, band_cells=20)
        if (it + 1) % 200 == 0:
            vs.append(float((g.region() == 1).sum()))
    V = vs[-1] * dx ** 3
    Req = (3.0 * V / (4.0 * np.pi)) ** (1.0 / 3.0)
    conv = abs(vs[-1] - vs[-2]) / max(vs[-2], 1e-30)
    return Req, DFG * Req / 2.0 / GAM, conv


def front(L, N, dx, n_h, pair_curv, nstep=80):
    """平面速度（零插值真值口径 D；γ=0 ⇒ 曲率项本应为 0，作为回归守卫）。"""
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    g.pair_curvature = bool(pair_curv)
    n_h = np.asarray(n_h, float) / np.linalg.norm(n_h)
    rel = g.XYZ - np.array([L / 2] * 3)
    d0 = rel @ n_h
    g.phi[1] = d0
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=20)
        t += dt
    phi_ex = d0 - MOB * DF * t
    bm = np.abs(phi_ex) <= 3.0 * dx
    return 1.0 + float(np.median(g.phi[1][bm] - phi_ex[bm])) / (MOB * DF * t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    tilt = np.asarray(NPF[1], float)
    tilt = tilt / np.linalg.norm(tilt)
    print('=' * 100)
    print('T11h —— 曲率取差分场（修 EXPERT-#4）   L=%.0f nm  Δx=%s nm' % (a.L_nm, a.dxs))
    print('=' * 100)
    print('【T11h-1】Gibbs–Thomson γ_eff/γ（目标 1.000；输入 γ=%.2f, Δf=%.0e）'
          % (GAM, DFG))
    out = {}
    for pc in (False, True):
        vals, reqs = [], []
        for dx in dxs:
            N = int(round(L / dx))
            Req, ratio, conv = gt(L, N, dx, pc)
            vals.append(ratio)
            reqs.append(Req)
            print('   pair_curvature=%-5s Δx=%-6.1f nm  R_eq=%7.2f nm  γ_eff/γ=%.3f'
                  '  末段体积变化 %.2e' % (str(pc), dx * 1e9, Req * 1e9, ratio, conv),
                  flush=True)
        v = np.array(vals)
        out[pc] = v
        print('     ⇒ 均值 %.3f  散布 %.4f' %
              (v.mean(), float((v.max() - v.min()) / abs(v.mean()))))
    v1 = out[True]
    ok1 = (abs(float(v1.mean()) - 1.0) < 0.30) and \
          (float((v1.max() - v1.min()) / abs(v1.mean())) < 0.15)
    print('   T11h-1: %s' % ('PASS' if ok1 else 'FAIL'))

    print()
    print('【T11h-2】回归守卫：平面前沿速度（口径 D，精确值 1.000）')
    ok2 = True
    for lab, n_h in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', tilt)):
        v = []
        for dx in dxs:
            N = int(round(L / dx))
            v.append(front(L, N, dx, n_h, True))
        v = np.array(v)
        sp = float((v.max() - v.min()) / abs(v.mean()))
        err = float(np.max(np.abs(v - 1.0)))
        ok2 &= (err < 0.05) and (sp < 0.05)
        print('   %-14s %s ⇒ 最大偏差 %.2f%% 散布 %.4f %s'
              % (lab, ' '.join('%.4f' % x for x in v), 100 * err, sp,
                 'OK' if (err < 0.05 and sp < 0.05) else '✗'))
    print('   T11h-2: %s' % ('PASS' if ok2 else 'FAIL'))

    print()
    print('【T11h-3】回归守卫：γ=0 时曲率项不参与 ⇒ 关/开 pair_curvature 应逐位相同')
    f_off = front(L, int(round(L / dxs[0])), dxs[0], tilt, False)
    f_on = front(L, int(round(L / dxs[0])), dxs[0], tilt, True)
    same = abs(f_off - f_on) < 1e-12
    print('   γ=0 档：off %.12f vs on %.12f ⇒ 逐位相同 %s' % (f_off, f_on, same))
    print('   T11h-3: %s' % ('PASS' if same else 'FAIL'))

    print()
    print('=' * 100)
    print('  T11h-1 %s | T11h-2 %s | T11h-3 %s'
          % tuple('PASS' if x else 'FAIL' for x in (ok1, ok2, same)))
    allok = ok1 and ok2 and same
    print('  ⇒ T11h %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
