#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_w7.py --- W-7：Window B 侧 **halo/core + domain-size 收敛**（第二版，隔离"边界效应"）。

★ 第一版的教训（记账）：把晶核数按**体积**放大后，小盒的 core（中心 50%³ = 1/8 体积）
  平均只含 12/8 = **1.5 个晶核** ⇒ 观测量被**成核统计**主导，而不是边界效应
  （实测 f_core 差 0.188 比 f_all 差 0.0066 还大 ⇒ 完全把两件事混在一起）。

第二版改成**同一个 core 实现**：先在小盒里生成晶核表 {(位置, 变体)}，然后把它**原样平移进
2L 盒的中心**（相对位置不变），再在**外围**补足到同密度。这样两次运行的 core 初值**逐胞相同**
⇒ core 观测量的差**只**来自外围（= 边界/有限尺寸效应），这正是 halo 要覆盖的东西。

判据：W7-1 |f_core(2L) - f_core(L)| < 0.05（core-out 有效）；
      W7-2 shell 的差 > core 的差；W7-3 记账 f_all 的差。
"""
import numpy as np

from windowB_surface import LevelSetMulti
from windowB_pf3d import C_cubic, _lam_full

ok = {}


def rec(tag, verdict, extra=''):
    ok[tag] = verdict
    print('   %-58s %-7s %s' % (tag, verdict, extra))


_epscache = {}


def eps_and_npref(C, rng, nv=12):
    if 'eps' not in _epscache:
        from windowB_ti64_variants import variants
        e, _F, _m = variants()
        _epscache['eps'] = e
    eps0 = _epscache['eps']
    if 'npref' not in _epscache:
        npf = {}
        for v in range(nv):
            best, bn = None, None
            for n in rng.normal(size=(120, 3)):
                n = n / np.linalg.norm(n)
                val = 0.5 * float(np.einsum('ij,ijkl,kl->', eps0[v], _lam_full(C, n), eps0[v]))
                if best is None or val < best:
                    best, bn = val, n
            npf[v + 1] = bn
        _epscache['npref'] = npf
    return eps0, _epscache['npref']


def make_nuclei(L, nseed, R, rng):
    out = []
    for _ in range(nseed):
        c = rng.random(3) * (L - 2 * R) + R
        out.append((c, int(rng.integers(1, 13))))
    return out


def build(N, dx, nuc, R, df, gamma=0.15, aniso=0.4, seed=0, Mob=1e-9):
    rng = np.random.default_rng(seed)
    C = C_cubic(134.0e9, 110.0e9, 36.0e9)
    eps0, npref = eps_and_npref(C, rng)
    nv = len(eps0)
    g = LevelSetMulti(N, N * dx, C=C, eps0=eps0, gamma=gamma, Mob=Mob,
                      df=[0.0] * (nv + 1), workers=4, reinit_every=25)
    for c, k in nuc:
        if np.all(c > 0) and np.all(c < N * dx):
            g.seed_plate(k, c, npref[k], R, 2.0 * dx)
    g.init_parent()
    g.c[:] = 0.036
    g.Gam_mol[:] = 0.0
    g.Gam[:] = 0.0
    g.df[1:] = df
    return g


def frac_in(reg, N, lo, hi):
    x = (np.arange(N) + 0.5) / N
    m = (x >= lo) & (x < hi)
    sub = reg[np.ix_(m, m, m)]
    return float((sub != 0).mean())


def run_pair(N1=32, N2=64, dx=1e-8, nstep=25, df=1e7, R_mult=0.22):
    L1, L2 = N1 * dx, N2 * dx
    R = R_mult * L1
    rng = np.random.default_rng(7)
    n1 = make_nuclei(L1, 12, R, rng)
    off = 0.5 * (L2 - L1)
    n2 = [(c + off, k) for (c, k) in n1]                       # ★ core 实现不变
    extra = make_nuclei(L2, 96 - 12, R, rng)
    for c, k in extra:                                          # 外围补核（同密度）
        if not (np.all(c > off - 1e-30) and np.all(c < off + L1 + 1e-30)):
            n2.append((c, k))
    out = {}
    for N, L, nuc in ((N1, L1, n1), (N2, L2, n2)):
        g = build(N, dx, nuc, R, df)
        dt = 0.15 * dx / (1e-9 * 1e8)
        for _ in range(nstep):
            g.advance(dt, aniso=0.4, npref=None, band_cells=20)
            g.update_Gamma(dt)
        reg = g.region()
        fa = float((reg != 0).mean())
        # core：2L 盒用"中心 L1 区域"，L 盒用"中心 50%"
        if N == N1:
            fc = frac_in(reg, N, 0.25, 0.75)
            fs = 1.0 - frac_in(reg, N, 0.125, 0.875)
        else:
            lo, hi = 0.5 * (1 - L1 / L2), 0.5 * (1 + L1 / L2)
            fc = frac_in(reg, N, lo, hi)
            fs = 1.0 - frac_in(reg, N, lo - 0.125 * (hi - lo), hi + 0.125 * (hi - lo))
        out[N] = (fa, fc, fs)
    return out


print('==== W-7 Window B 侧 halo/core + domain-size 收敛（同 core 实现）====')
dx = 1e-8
o = run_pair(dx=dx)
fa1, fc1, fs1 = o[32]
fa2, fc2, fs2 = o[64]
print('   %-12s %10s %10s %10s' % ('盒子', 'f_all', 'f_core', 'f_shell'))
print('   %-12s %10.4f %10.4f %10.4f' % ('L=32dx', fa1, fc1, fs1))
print('   %-12s %10.4f %10.4f %10.4f' % ('L=64dx', fa2, fc2, fs2))
d_all, d_core, d_shell = abs(fa2 - fa1), abs(fc2 - fc1), abs(fs2 - fs1)
print('   |差|         %10.4f %10.4f %10.4f' % (d_all, d_core, d_shell))
rec('W7-1 f_core（同 core 实现）对盒子尺寸收敛（|d| < 0.05）',
    'PASS' if d_core < 0.05 else 'FAIL', 'd_core=%.4f' % d_core)
rec('W7-2 壳层的差 > core 的差（边界效应真实存在 => halo 必要）',
    'PASS' if d_shell > d_core else 'FAIL', 'shell=%.4f vs core=%.4f' % (d_shell, d_core))
rec('W7-3 记账：f_all 的差 vs f_core 的差', 'PASS',
    'd_all=%.4f ; d_core=%.4f' % (d_all, d_core))
nP = sum(1 for v in ok.values() if v == 'PASS')
print()
print('W-7 汇总: PASS %d / FAIL %d' % (nP, sum(1 for v in ok.values() if v == 'FAIL')))
