#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计 · Q5 —— ψ 通道的**行为**复核（为什么 `_bk_psi_wire.py` W-2/W-3 FAIL）。

装置：3 根同变体板条（γ0=0.25，Δx=125 nm），`g.film` 打开，`psi0=0.99`，
固定初始 F3 掩模 vs 当前 F3 掩模两种平均 —— 判"非单调"是**物理**还是**量具**。

对照：
  · 正对照  γ_f = 0.60 > γ_dry（本项目 C-1 情形）⇒ ψ 应单调退湿（P-2）
  · 反对照  γ_f = 0.02 < γ_dry ⇒ ψ 应单调湿润
  · 零步对照 psi0=1.0  ⇒ ψ 应**一步都不动**（精确不动点）
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

N, L = 32, 4.0e-6
DX = L / N                                  # 125 nm
G0 = 0.25
T_LATH, W_LATH, L_LATH = 635e-9, 1224.153e-9, 2000e-9
KW = dict(aniso=0.4, band_cells=20, mob_beta=6.620727, mob_beta_w=2.3,
          adv_grad='proj2', norm_smooth=0, facet_lam=0.0, facet_eps=0.05,
          herring=True)
DF = 1.85e8


def build(film=None, nv=3):
    lt = WL.LathTable([1] * nv, omegas=WL.default_omega(nv, 5.0),
                      eps0_var=EPS0, npref_var=NPF, gamma0=G0)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(nv)]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float) for i in range(nv)}
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=G0, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=1, reinit_every=0,
                        reinit_dt=1e-4, reinit_band_cells=6.0)
    g.lath = lt
    g.npref_tab = npref
    if film is not None:
        g.film = dict(film)
    nh = np.asarray(NPF[1], float); nh /= np.linalg.norm(nh)
    aa = np.asarray(g.atab[1], float); aa /= np.linalg.norm(aa)
    c0 = np.array([L / 2] * 3)
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * T_LATH * 0.85    # ★ 重叠 15% ⇒ t=0 就有 F3 胞
        g.seed_plate(i + 1, c0 + off * nh, nh, W_LATH / 2, T_LATH,
                     elong=L_LATH / W_LATH, along=aa, flat_end=True)
    g.init_parent()
    return g, lt, npref


def f3mask(g, lt):
    karr, larr = g.par.argmin2(g.phi)
    G = lt.gtab[np.clip(karr.astype(np.intp), 0, g.nreg - 1),
                np.clip(larr.astype(np.intp), 0, g.nreg - 1)]
    return np.isfinite(G)


def run(film, nstep=90, psi0_label=''):
    g, lt, npref = build(film)
    if film is not None:
        g.psi = np.full(g.phi.shape[1:], float(film.get('psi0', 1.0)))
    dt = 0.15 * DX / (MOB * DF)
    masks, psis = [], []
    for it in range(nstep + 1):
        masks.append(f3mask(g, lt))
        psis.append(None if g.psi is None else g.psi.copy())
        if it == nstep:
            break
        g.advance(dt, npref=npref, **KW)
    masks = np.array(masks)
    ncur = masks.reshape(len(masks), -1).sum(1)
    if psis[0] is None:
        return None, masks, ncur, g, None
    psis = np.array(psis)
    n_any = masks.any(0)                       # 曾进过带的胞
    persist = masks.all(0)                     # **全程都在带内**的胞
    out = {}
    out['cur'] = np.array([psis[i][masks[i]].mean() if masks[i].any() else np.nan
                           for i in range(len(masks))])
    out['any'] = np.array([psis[i][n_any].mean() for i in range(len(psis))])
    out['persist'] = (np.array([psis[i][persist].mean() for i in range(len(psis))])
                      if persist.any() else np.array([np.nan]))
    return out, masks, ncur, g, persist


def report(tag, out, ncur, persist):
    if out is None:
        print('[%s] g.psi is None ⇒ 通道关闭' % tag)
        return
    npc = int(persist.sum()) if persist is not None else 0
    print('[%s]  全程在带内的胞 = %d ；带胞数 %d → %d' % (tag, npc, ncur[0], ncur[-1]))
    for key, lbl in (('cur', '当前带平均'), ('any', '曾进带胞平均'),
                     ('persist', '全程在带胞平均')):
        v = out[key]
        mono = bool(np.all(np.diff(v) <= 1e-12))
        print('   ψ(%s) %.4f → %.4f ；单调不增=%s ；Δmax=%.2e'
              % (lbl, v[0], v[-1], mono, float(np.max(np.diff(v))) if v.size > 1 else 0.0))
    print('   ψ_全程带 历史(每 10 步): %s'
          % np.array2string(out['persist'][::10], precision=4))


def main():
    t0 = time.time()
    print('=' * 100)
    print('R30-PSI  Δx=%.1f nm  3 根同变体  1 对 F3(θ=5° ⇒ γ_dry=%.4f)  β_h=6.620727'
          % (DX * 1e9, float(np.nanmax([0.277088]))))
    print('=' * 100)

    cases = [('正对照 γ_f=0.60 > γ_dry', dict(gamma_f=0.60, W=0.05, L=1e8, psi0=0.99)),
             ('反对照 γ_f=0.02 < γ_dry', dict(gamma_f=0.02, W=0.05, L=1e8, psi0=0.01)),
             ('零步对照 psi0=1.0（精确不动点）', dict(gamma_f=0.60, W=0.05, L=1e8, psi0=1.0))]
    for tag, film in cases:
        out, masks, ncur, g, persist = run(film)
        print('-' * 100)
        report(tag, out, ncur, persist)

    # 关闭对照：film=None ⇒ psi 不分配
    out, masks, ncur, g, persist = run(None)
    print('-' * 100)
    print('[负对照 film=None] g.psi is None = %s（⇒ 整条通道关闭）' % (g.psi is None))
    print('总耗时 %.1f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
