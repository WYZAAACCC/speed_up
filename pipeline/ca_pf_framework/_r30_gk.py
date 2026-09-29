#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计 · Q3 —— **γ_LAGB 的驱动通道与 γκ/Δf 量级（实测）**。

装置（与闭环 `cln11` 同口径的**等效**小装置）：
  Δx = 125 nm（= 闭环值）、γ0 = 0.25（= 闭环值）、板条厚 635 nm、长 4590 nm、宽 1224 nm、
  β_h=3.5 / β_w=2.3、adv_grad=proj2、norm_smooth=0、herring=True、facet_lam=0、
  3 根**同变体**（v=1）板条沿 n* 堆叠（θ 阶梯 0/2.5/5° ⇒ γ_RS = 0.1843/0.2771）。

★★ 关键：`advance` 默认 `pair_curvature=True` ⇒ 进驱动的 κ **不是** winner 场自己的
   `curvature_of(k)`，而是**差分场** `κ = σ·div(∇(σ(φ_k−φ_l))/|·|)`（`windowB_surface.py:3150-3177`）。
   本脚本按**默认路径**复现，同时把两种 κ 都量出来对比。

测什么
  1. F3 胞上**进驱动的 κ** 分布（max/p99/p90/p50/mean）
  2. **γ 是否只从 `−stk·κ` 进来**：逐胞核对 §5.1  `dG == (Δdf)+(Δed)−stk·κ`；
     并单独报 F3 上 (Δdf)、(Δed) 是不是**逐位 0**
  3. **γκ/Δf** 分布（= |dG_F3|/Δf）
  4. 对照：无扰动（负） / 加扰动（正，κ≠0） / γ_F3=0（通道上界）
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, MOB                    # noqa: E402

N, L = 48, 6.0e-6
DX = L / N
G0 = 0.25
T_LATH, W_LATH, L_LATH = 635e-9, 1224.153e-9, 4590e-9
DF_LO, DF_HI = 1.5e8, 2.2e8
KW = dict(aniso=0.4, band_cells=20, mob_beta=3.5, mob_beta_w=2.3,
          adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05,
          herring=True)

XYZ = np.stack(np.meshgrid(np.arange(N) * DX, np.arange(N) * DX,
                           np.arange(N) * DX, indexing='ij'), -1)


def build(df, gtab_override=None, nv=3, om_max=5.0):
    lt = WL.LathTable([1] * nv, omegas=WL.default_omega(nv, om_max),
                      eps0_var=EPS0, npref_var=NPF, gamma0=G0)
    if gtab_override is not None:
        lt.gtab[np.isfinite(lt.gtab)] = float(gtab_override)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(nv)]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float) for i in range(nv)}
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=G0, Mob=MOB,
                        df=[0.0] + [df] * nv, workers=1, reinit_every=0,
                        reinit_dt=1e-4, reinit_band_cells=6.0)
    g.lath = lt
    g.npref_tab = npref
    nh = np.asarray(NPF[1], float); nh /= np.linalg.norm(nh)
    aa = np.asarray(g.atab[1], float); aa /= np.linalg.norm(aa)
    c0 = np.array([L / 2] * 3)
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * T_LATH
        g.seed_plate(i + 1, c0 + off * nh, nh, W_LATH / 2, T_LATH,
                     elong=L_LATH / W_LATH, along=aa, flat_end=True)
    g.init_parent()
    return g, lt, nh, npref


def state(g, lt, npref):
    """按 `advance` 的**默认路径**逐胞复现：karr/larr、进驱动的 κ、stk、γ_Σ。"""
    karr, larr = g.par.argmin2(g.phi)
    karr = karr.astype(np.intp); larr = larr.astype(np.intp)
    G = lt.gtab[np.clip(karr, 0, g.nreg - 1), np.clip(larr, 0, g.nreg - 1)]
    isF3 = np.isfinite(G)
    pha = np.take_along_axis(g.phi, karr[None], 0)[0]
    phb = np.take_along_axis(g.phi, larr[None], 0)[0]
    sg = np.where(karr < larr, 1.0, -1.0)
    dd = sg * (pha - phb)
    gd = g.par.gradient(dd, g.dx, edge_order=2)
    gn = np.sqrt(sum(t ** 2 for t in gd)) + 1e-30
    kap_diff = sg * g.curvature_of(0, grad=gd, gn=gn)      # ← 默认路径用的 κ
    kap_w = np.zeros_like(kap_diff)
    stk = np.zeros_like(kap_diff)
    for k in np.unique(karr[isF3]):
        k = int(k)
        gk = g.par.gradient(g.phi[k], g.dx, edge_order=2)
        gnk = np.sqrt(sum(t ** 2 for t in gk)) + 1e-30
        kw = g.curvature_of(k, grad=gk, gn=gnk)
        nref = g.facet_nref(k, larr, npref)
        ss = g._stiff_of(k, gk, gnk, npref, KW['aniso'],
                         np.where(isF3, G, G0), True, KW['facet_lam'],
                         KW['facet_eps'], nref_cell=nref)
        m = isF3 & (karr == k)
        kap_w[m] = kw[m]
        stk[m] = ss[m] if np.ndim(ss) else float(ss)
    return karr, larr, isF3, kap_diff, kap_w, stk, G


def pct(a, q):
    return float(np.percentile(np.abs(a), q)) if np.size(a) else float('nan')


def arm(df, gtab_override=None, nstep=24, perturb=False):
    g, lt, nh, npref = build(df, gtab_override)
    if perturb:
        aa = np.asarray(g.atab[1], float); aa /= np.linalg.norm(aa)
        pa = XYZ[..., 0] * aa[0] + XYZ[..., 1] * aa[1] + XYZ[..., 2] * aa[2]
        bump = (0.5 * g.dx) * np.cos(2.0 * np.pi * pa / (4.0 * g.dx))
        band = np.abs(g.phi[2]) < 3.0 * g.dx
        g.phi[2] = g.phi[2] + np.where(band, bump, 0.0)
    rec = dict(kdiff=[], kw=[], ratio=[], chk=[], nF3=[],
               df0=None, ed0=None, pos=[])
    dt = 0.15 * DX / (MOB * df)
    t = 0.0
    for it in range(nstep + 1):
        karr, larr, isF3, kd, kw, stk, G = state(g, lt, npref)
        if isF3.any():
            dfd = (g.df[karr] - g.df[larr])
            edk, edl = g.elastic_driving_pair(karr, larr)
            edd = edk - edl
            if rec['df0'] is None:
                rec['df0'] = float(np.max(np.abs(dfd[isF3])))
                rec['ed0'] = float(np.max(np.abs(edd[isF3])))
            rec['kdiff'].append(np.abs(kd[isF3]).copy())
            rec['kw'].append(np.abs(kw[isF3]).copy())
            rec['nF3'].append(int(isF3.sum()))
            m12 = isF3 & (((karr == 1) & (larr == 2)) | ((karr == 2) & (larr == 1)))
            if m12.any():
                rec['pos'].append((t, float((XYZ[m12] @ nh).mean()), int(m12.sum())))
        if it == nstep:
            break
        g.advance(dt, npref=npref, **KW)
        t += dt
        # advance 之后：用**步首**的 κ/stk 核对 dG（advance 内 dG 用的就是步首 φ）
        if isF3.any() and hasattr(g, '_dG_cell_ref'):
            dG = np.asarray(g._dG_cell_ref)
            rhs = (dfd + edd - stk * kd)
            rec['chk'].append(float(np.max(np.abs(dG[isF3] - rhs[isF3]))))
            rec['ratio'].append(np.abs(dG[isF3]) / df)
    return g, lt, rec, dt


def show(tag, K, Kw, R, frac=1.0):
    if not np.size(K):
        print('  %-14s （无 F3 胞）' % tag)
        return
    print('  %-14s n=%7d | κ_diff max=%.4e p99=%.4e p90=%.4e p50=%.4e | '
          'κ_winner max=%.4e p50=%.4e | max·Δx=%.3f'
          % (tag, K.size, K.max(), pct(K, 99), pct(K, 90), pct(K, 50),
             Kw.max() if np.size(Kw) else float('nan'),
             pct(Kw, 50) if np.size(Kw) else float('nan'), K.max() * DX))
    if np.size(R):
        print('  %-14s γκ/Δf  max=%.5f p99=%.5f p90=%.5f p50=%.5f mean=%.5f'
              % ('', R.max() * frac, pct(R, 99) * frac, pct(R, 90) * frac,
                 pct(R, 50) * frac, R.mean() * frac))


def main():
    t0 = time.time()
    DF = 1.85e8
    print('=' * 108)
    print('R30-GK  Δx=%.1f nm  L=%.1f µm  γ0=%.2f  板条厚=%.0f nm  3 根同变体(v=1)  Δf=%.2e'
          % (DX * 1e9, L * 1e6, G0, T_LATH * 1e9, DF))
    print('=' * 108)

    for tag, pert, ov in (('A 无扰动', False, None),
                          ('B 加扰动', True, None),
                          ('C γ_F3=0', False, 0.0)):
        g, lt, rec, dt = arm(DF, ov, nstep=24, perturb=pert)
        K = np.concatenate(rec['kdiff']) if rec['kdiff'] else np.array([])
        Kw = np.concatenate(rec['kw']) if rec['kw'] else np.array([])
        R = np.concatenate(rec['ratio']) if rec['ratio'] else np.array([])
        print('-' * 108)
        print('[%s]  dt=%.4e s  24 步 ⇒ t_sim=%.3e s   F3 胞数 %s'
              % (tag, dt, 24 * dt, rec['nF3'][:1] + rec['nF3'][-1:]))
        show(tag, K, Kw, R)
        if rec['chk']:
            print('  %-14s §5.1 逐位核对 max|dG − [(Δdf)+(Δed)−stk·κ]| = %.3e'
                  % ('', max(rec['chk'])))
            print('  %-14s F3 上 max|Δdf| = %.3e  max|Δed| = %.3e'
                  % ('', rec['df0'], rec['ed0']))
        if len(rec['pos']) > 1:
            p = rec['pos']
            print('  %-14s F3(1,2) 沿 n* 位置: %.2f nm → %.2f nm ⇒ Δ=%+.5f Δx (%d 胞, %d 采样)'
                  % ('', p[0][1] * 1e9, p[-1][1] * 1e9,
                     (p[-1][1] - p[0][1]) / DX, p[-1][2], len(p)))
            if np.size(K):
                Meff = MOB * np.exp(-3.5)
                gam = float(np.median(lt.gtab[np.isfinite(lt.gtab)]))
                print('  %-14s [推理] 解析 d=M_effγ_Σκt（γ_Σ=%.4f, t=%.2e s）: '
                      'κ=p50 %.4f Δx | κ=max %.4f Δx'
                      % ('', gam, 24 * dt, Meff * gam * pct(K, 50) * 24 * dt / DX,
                         Meff * gam * K.max() * 24 * dt / DX))
        if tag.startswith('A'):
            gA = g
        if tag.startswith('B'):
            gB = g
        if tag.startswith('C'):
            d = float(np.max(np.abs(gA.phi - g.phi)))
            print('  [对照] γ_F3=0 vs RS（同装置无扰动，24 步）: max|Δφ| = %.4e m '
                  '= %.5f Δx；region 翻转 = %d'
                  % (d, d / DX, int((gA.region() != g.region()).sum())))
    print('-' * 108)
    print('总耗时 %.1f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
