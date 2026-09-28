#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T13_recheck_wrap.py --- T13-A 的**绕盒复核**（保护已报出的 PASS）。

为什么要复核
-----------
`T13-A` 是在 `T12-D12a` 的绕盒守卫**之前**跑的 ⇒ 那三个采样点是否已绕盒**未知**。
而 `T16` 首次运行正是在 `f≈0.03` 就绕盒（薄板面内长得快）⇒ 同类风险真实存在。
若 T13-A 的采样点已绕盒，则"厚度 ∝ `N_v^{-1/3}`"的三档读数要打折扣。

几何预估（**待实测确认**）
------------------------
种子间距 `d = ρ^{-1/3} = 1.109 µm`；绕盒条件 ≈ 面内半径 > `L/2 = 1.6 µm`。
`d < L/2` ⇒ 应当**碰撞先于绕盒** ✓ —— 但要实测。

判据
----
  T13-R1 三档在采样步**都不得绕盒**（`wrap_axes` 为空）
  T13-R2 若都通过，则原 `T13-A` 的结论**站得住**；否则标注失效范围

用法：python3 T13_recheck_wrap.py [--L-um 3.2] [--dx-nm 62.5] [--f-target 0.30]
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

DF, MOB = 2.0e8, 1e-9
R_SEED, T_SEED = 0.30e-6, 1.0e-7
RHO = 24.0 / (3.2e-6) ** 3
N0 = 8


def corr_1e(chi, dx):
    x = chi.astype(np.float64)
    y = x - x.mean()
    F = np.fft.fftn(y)
    ac = np.real(np.fft.ifftn(F * np.conj(F))) / x.size
    ac = np.fft.fftshift(ac)
    ctr = np.array(ac.shape) // 2
    zz, yy, xx = np.indices(ac.shape)
    rr = np.sqrt((xx - ctr[2]) ** 2 + (yy - ctr[1]) ** 2 + (zz - ctr[0]) ** 2)
    nb = int(min(ac.shape) // 2)
    prof = np.full(nb, np.nan)
    for i in range(nb):
        m = (rr >= i) & (rr < i + 1)
        if m.any():
            prof[i] = ac[m].mean()
    if not np.isfinite(prof[0]) or prof[0] <= 0:
        return np.nan
    idx = np.where(prof <= prof[0] / np.e)[0]
    if idx.size == 0:
        return np.nan
    i = int(idx[0])
    if i == 0:
        return 0.0
    t = (prof[i - 1] - prof[0] / np.e) / max(prof[i - 1] - prof[i], 1e-300)
    return float((i - 1 + t) * dx)


def run(L, dx, nseed, f_target):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=NV, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=4, reinit_every=0,
                        reinit_dt=6.0e-7)
    rng = np.random.default_rng(7)
    ns = 0
    for _ in range(nseed * 8):
        if ns >= nseed:
            break
        c = rng.random(3) * (L - 2 * (R_SEED + 0.3e-6)) + (R_SEED + 0.3e-6)
        k = int(rng.integers(1, NV + 1))
        nrm = np.asarray(NPF[k], float)
        nrm = nrm / np.linalg.norm(nrm)
        try:
            g.seed_plate(k, c, nrm, R_SEED, T_SEED)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    first_wrap = None
    for it in range(1, 600):
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20, mob_beta=3.5, mob_beta_w=2.3)
        if it % 5 == 0 and g.wrap_axes():
            first_wrap = it
            break
        if it % 5 == 0:
            f = 1.0 - float((g.region() == 0).sum()) / g.N ** 3
            if f >= f_target:
                break
    reg = g.region()
    f = 1.0 - float((reg == 0).sum()) / g.N ** 3
    vals = []
    for k in range(1, g.nreg):
        chi = (reg == k)
        if chi.sum() < 8:
            continue
        rc = corr_1e(chi, dx)
        if np.isfinite(rc):
            vals.append(rc)
    return dict(ns=ns, it=it, f=f, t=float(np.mean(vals)) if vals else np.nan,
                wrap=g.wrap_axes(), first_wrap=first_wrap)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-um', type=float, default=3.2)
    ap.add_argument('--dx-nm', type=float, default=62.5)
    ap.add_argument('--f-target', type=float, default=0.30)
    a = ap.parse_args()
    L, dx = a.L_um * 1e-6, a.dx_nm * 1e-9
    print('=' * 100)
    print('T13 绕盒复核   L=%.1f µm Δx=%.0f nm ρ=%.3f /µm³ ⇒ d=ρ^(-1/3)=%.3f µm，'
          'L/2=%.3f µm' % (a.L_um, a.dx_nm, RHO * 1e-18, RHO ** (-1 / 3.0) * 1e6, L / 2 * 1e6))
    print('=' * 100)
    rows = []
    for mult in (1, 3, 8):
        r = run(L, dx, N0 * mult, a.f_target)
        rows.append((mult, r))
        print('  N_v ×%-2d（%2d 核） step=%-4d f=%.4f  t=%.1f nm  '
              '**wrap_axes=%s**（首次触发步 %s）'
              % (mult, r['ns'], r['it'], r['f'], r['t'] * 1e9, r['wrap'],
                 r['first_wrap']), flush=True)
    ok = all(r[1]['wrap'] == [] for r in rows)
    tt = np.array([r[1]['t'] for r in rows])
    mult = np.array([r[0] for r in rows], float)
    p = float(np.polyfit(np.log(mult), np.log(tt), 1)[0])
    print()
    print('  T13-R1（三档采样时都未绕盒）: %s' % ('PASS' if ok else 'FAIL'))
    print('  复现的厚度定标指数 = %.3f（原 T13-A 报 −0.283；理论 −0.333）' % p)
    print('  ⇒ 原 T13-A 结论 %s' % ('**站得住**（采样点在未绕盒区间内）' if ok
                                   else '**需要标注失效范围**'))
    print('=' * 100)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
