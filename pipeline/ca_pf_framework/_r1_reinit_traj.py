#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_traj.py --- R1 reinit 审计（第 5 步）：**端到端轨迹对照**（Q-C 最强证据）。

★ 只读引擎；**不改任何引擎代码**。唯一的旋钮是 `g.reinit_iters`（实例属性，
  引擎 `sussman_reinit` 本来就按 `self.reinit_iters` 取）。

做法：**同一条真实生长轨迹**（N=96 Δx=250 nm L=24 µm，8 个核、8 个不同变体，
`reinit_dt=6.0e-7` = 生产触发口径，40 步）跑 4 个臂，**只差 `reinit_iters`**：
    iters ∈ {100（生产现值）, 50, 36, 20}
逐步记录：步时、该步是否发生 reinit、该次 reinit 的 done/skipped、界面键、f。
末态对照：`region()` 逐胞翻转数、`max|Δφ|/dx`、逐变体胞数、`r_c^var`（厚度）、界面键。

⇒ 直接回答"降低 iters 后**物理**出不出问题"，而不是只看单次算子。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic                                # noqa: E402
from windowB_pf3d import argmin_normal as _argmin_normal        # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
MOB, DF = 1e-9, 3.5e8
NPF = {v + 1: _argmin_normal(C, np.asarray(EPS0[v], float))[0] for v in range(NV)}
N, DX = 96, 250e-9
L = N * DX
NSTEP = 40
REINIT_DT = 6.0e-7
ARMS = [100, 50, 36, 20]


def band_bonds(reg):
    n = 0
    for ax in range(3):
        n += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return n


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


def build():
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                        reinit_dt=REINIT_DT, reinit_band_cells=6.0)
    rng = np.random.default_rng(7)
    step = L / 2.0
    ns = 0
    R, t, jit = 1.5e-6, 0.9e-6, 0.25
    for i in range(2):
        for j in range(2):
            for k in range(2):
                c = np.array([(i + 0.5) * step, (j + 0.5) * step,
                              (k + 0.5) * step]) + (rng.random(3) - 0.5) * jit * step
                kk = ns + 1
                nrm = np.asarray(NPF[kk], float)
                g.seed_plate(kk, c, nrm / np.linalg.norm(nrm), R, t)
                ns += 1
    g.init_parent()
    return g, ns


def main():
    print('=' * 116)
    print('R1 reinit 审计 / 端到端轨迹对照：**只差 `reinit_iters`**')
    print('  N=%d Δx=%.0f nm L=%.1f µm %d 步  reinit_dt=%.1e s（生产口径）  dt=%.4e s'
          % (N, DX * 1e9, L * 1e6, NSTEP, REINIT_DT, 0.15 * DX / (MOB * DF)))
    print('  臂：iters = %s' % ARMS)
    print('=' * 116)
    out = {}
    g = build()
    dt = 0.15 * DX / (MOB * DF)
    for arm in ARMS:
        g.phi = np.full((g.nreg, N, N, N), 1e3)
        rng = np.random.default_rng(7)
        step = L / 2.0
        ns = 0
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    c = np.array([(i + 0.5) * step, (j + 0.5) * step,
                                  (k + 0.5) * step]) + \
                        (rng.random(3) - 0.5) * 0.25 * step
                    kk = ns + 1
                    nrm = np.asarray(NPF[kk], float)
                    g.seed_plate(kk, c, nrm / np.linalg.norm(nrm), 1.5e-6, 0.9e-6)
                    ns += 1
        g.init_parent()
        g.reinit_iters = arm
        g.reinit_dt = REINIT_DT
        g._t_since_reinit = 0.0
        g._cnt = 0
        g._reinit_done = g._reinit_skipped = g._reinit_reg_flips = 0
        g._reinit_reg_flips_last = 0
        print()
        print('  ---- 臂 iters=%d ----' % arm, flush=True)
        t0 = time.time()
        tmax = 0.0
        tadv = 0.0
        nre = 0
        tot_done = tot_skip = tot_flip = 0
        for it in range(1, NSTEP + 1):
            ts = time.time()
            g.elastic_driving()
            g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                      mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
            el = time.time() - ts
            fired = (getattr(g, '_t_since_reinit', 1.0) == 0.0)
            tmax = max(tmax, el)
            if fired:
                nre += 1
                tadv += el
                reg = g.region()
                tot_done += getattr(g, '_reinit_done', 0)
                tot_skip += getattr(g, '_reinit_skipped', 0)
                tot_flip += int(getattr(g, '_reinit_reg_flips_last', 0))
                print('     step %-3d **reinit 触发** 步时=%7.2f s  界面键=%d  '
                      'done/累计=%d skip/累计=%d'
                      % (it, el, band_bonds(reg),
                         getattr(g, '_reinit_done', 0),
                         getattr(g, '_reinit_skipped', 0)), flush=True)
            elif it % 10 == 0:
                print('     step %-3d 步时=%.2f s  累计=%.1f s'
                      % (it, el, time.time() - t0), flush=True)
        reg = g.region()
        f = 1.0 - float((reg == 0).sum()) / g.N ** 3
        nb = band_bonds(reg)
        tvar = []
        for k in range(1, g.nreg):
            chi = (reg == k)
            if chi.sum() < 8:
                continue
            rc = corr_1e(chi, g.dx)
            if np.isfinite(rc):
                tvar.append(rc)
        vols = [int((reg == k).sum()) for k in range(g.nreg)]
        tot = time.time() - t0
        print('     ⇒ 总时 %.1f s  最慢步 %.2f s（其中含 reinit 的步累计 %.1f s）  '
              'reinit 次数=%d  Σdone=%d Σskip=%d Σ翻转=%d'
              % (tot, tmax, tadv, nre, tot_done, tot_skip, tot_flip), flush=True)
        print('     ⇒ 末态 f=%.5f 界面键=%d  r_c^var=%.1f nm  逐变体胞数=%s'
              % (f, nb, (np.mean(tvar) * 1e9 if tvar else np.nan), vols), flush=True)
        out[arm] = dict(f=f, nb=nb, tvar=(float(np.mean(tvar)) if tvar else np.nan),
                        phi=g.phi.copy(), reg=reg.copy(), tot=tot, vols=vols,
                        done=tot_done, skip=tot_skip, flips=tot_flip)
    # ---- 交叉对照 ----
    ref = out[100]
    print()
    print('=' * 116)
    print('  交叉对照（基准 = iters=100）')
    print('  %6s %10s %12s %12s %14s %12s %12s' %
          ('iters', 'f', 'region翻转', 'max|Δφ|/dx', '中位|Δφ|/dx', '界面键比',
           'r_c^var 比'))
    for arm in ARMS:
        o = out[arm]
        fl = int((o['reg'] != ref['reg']).sum())
        d = np.abs(o['phi'] - ref['phi'])
        bandm = np.abs(ref['phi']).min(axis=0) <= 6.0 * g.dx
        print('  %6d %10.5f %12d %12.3e %14.3e %12.5f %12.5f'
              % (arm, o['f'], fl, float(d.max()) / g.dx,
                 float(np.median(d[bandm] if bandm.any() else d)) / g.dx,
                 o['nb'] / ref['nb'],
                 (o['tvar'] / ref['tvar']) if ref['tvar'] else np.nan), flush=True)
    print()
    print('  ⚠ 记账：本轨迹是**同一物理**、**同一初值**、**同一触发频率**，'
          '臂间唯一差异是 `reinit_iters`。')
    print('=' * 116)
    return 0


if __name__ == '__main__':
    sys.exit(main())
