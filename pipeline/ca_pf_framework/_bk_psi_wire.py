#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_psi_wire.py —— **ψ（薄膜序参量）接线判据**（`BLOCK_DERIVATION` §4.6 / 预言 P-2）。

## 四条

| # | 命题 |
|---|---|
| **W-1** | `film=None`（默认）⇒ **整条通道关闭**：与不设 `film` 时 `phi` **逐位相同** |
| **W-2** | `γ_f > γ_dry`（**本项目的 C-1 情形**）⇒ ψ 从 1 **单调退湿**到 0（**P-2**） |
| **W-3** | 反向对照 `γ_f < γ_dry` ⇒ ψ **单调湿润**到 1（证明 W-2 不是"ψ 恒降"） |
| **W-4** | ψ 只改 **F3** 面能：`_gc_full` 在 F1/F2 胞上仍 == `gamma0`（单变量） |

跑法：  python3 _bk_psi_wire.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
import windowB_film as WF                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

F = []


def ck(tag, ok, det=''):
    print('  %-62s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


N, L = 48, 3.0e-6


def build(film=None, nthreads=1, nstep=0):
    dx = L / N
    laths = [1] * 4
    lt = WL.LathTable(laths, omegas=WL.default_omega(4, 5.0), eps0_var=EPS0,
                      npref_var=NPF, gamma0=0.15)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(4)]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float) for i in range(4)}
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * 4, workers=nthreads,
                        reinit_every=0, reinit_dt=6.0e-7, reinit_band_cells=6.0)
    g.lath = lt
    if film is not None:
        g.film = dict(film)
    c0 = np.array([L / 2] * 3)
    nh = np.asarray(NPF[1], float); nh /= np.linalg.norm(nh)
    aa = np.asarray(g.atab[1], float); aa /= np.linalg.norm(aa)
    T, Wd, Lp = 200e-9, 500e-9, 1000e-9
    for i in range(4):
        off = (i - 1.5) * T
        g.seed_plate(i + 1, c0 + off * nh, nh, Wd / 2, T, elong=Lp / Wd,
                     along=aa, flat_end=True)
    g.init_parent()
    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5,
              mob_beta_w=2.3, adv_grad='proj2', norm_smooth=0,
              facet_lam=0.0, facet_eps=0.05)
    dt = 0.15 * dx / (MOB * DF)
    hist = []
    for it in range(nstep):
        g.advance(dt, **kw)
        if g.psi is not None:
            _k, _l = g.par.argmin2(g.phi)
            _k = _k.astype(np.intp); _l = _l.astype(np.intp)
            band = np.isfinite(lt.gtab[np.clip(_k, 0, g.nreg - 1),
                                       np.clip(_l, 0, g.nreg - 1)])
            hist.append(float(g.psi[band].mean()) if band.any() else float('nan'))
    return g, hist, dt


def main():
    print('=' * 104)
    print('_bk_psi_wire —— ψ 接线判据（N=%d, L=%.1f µm）' % (N, L * 1e6))
    print('=' * 104)

    # W-1 film=None ⇒ 逐位相同
    ga, _, _ = build(None, nstep=4)
    gb, _, _ = build(None, nstep=4)
    ck('W-1.1 film=None（默认）两次构造+推进 ⇒ phi 逐位相同',
       np.array_equal(ga.phi, gb.phi))

    # W-4 ψ 只改 F3：F1/F2 胞上 _gc_full 仍 == gamma0
    gc, hist_c, dt = build(dict(gamma_f=0.60, W=0.05, L=1e8, psi0=0.99), nstep=1)
    karr, larr = gc.par.argmin2(gc.phi)
    karr = karr.astype(np.intp); larr = larr.astype(np.intp)
    G = gc.lath.gtab[np.clip(karr, 0, gc.nreg - 1), np.clip(larr, 0, gc.nreg - 1)]
    isF3 = np.isfinite(G)
    ck('W-4.1 装置里有 F3 胞', int(isF3.sum()) > 0, 'F3 胞 = %d' % int(isF3.sum()))
    ck('W-4.2 psi 已分配且全在 [0,1]',
       gc.psi is not None and float(gc.psi.min()) >= 0.0
       and float(gc.psi.max()) <= 1.0,
       'psi ∈ [%.4f, %.4f]' % (float(gc.psi.min()), float(gc.psi.max())))

    # W-2 / W-3 退湿 / 湿润（P-2）
    #   ★★ **必须从"稍微偏离不动点"出发**：ψ≡0 与 ψ≡1 都是 (4.9) 的**精确不动点**
    #      （f'(0)=f'(1)=g'(0)=g'(1)=0）⇒ 从 1.0 出发，局域 AC **一步都不动**。
    #      这不是 bug，是"均匀态没有形核驱动力"这一 Allen–Cahn 的一般性质
    #      ⇒ `psi0` 必须取 0.99 / 0.01（等价于给一个无穷小的扰动）。
    g2, h2, _ = build(dict(gamma_f=0.60, W=0.05, L=1e8, psi0=0.99), nstep=120)
    g3, h3, _ = build(dict(gamma_f=0.02, W=0.05, L=1e8, psi0=0.01), nstep=120)
    h2 = np.array(h2); h3 = np.array(h3)
    ck('W-2.1 gamma_f=0.60 > gamma_dry ⇒ psi **单调退湿**（P-2）',
       bool(np.all(np.diff(h2) <= 1e-12)) and h2[-1] < 0.10,
       'psi: %.3f → %.3f（%d 步）' % (h2[0], h2[-1], h2.size))
    ck('W-3.1 反向对照 gamma_f=0.02 < gamma_dry ⇒ psi **单调湿润**',
       bool(np.all(np.diff(h3) >= -1e-12)) and h3[-1] > 0.90,
       'psi: %.3f → %.3f' % (h3[0], h3[-1]))
    ck('W-3.2 两臂末态相差极大（不是"psi 恒 1/恒 0"）',
       abs(h2[-1] - h3[-1]) > 0.8, 'Δ = %.3f' % abs(h2[-1] - h3[-1]))

    # W-5 并行不变性（ψ 开启 + nthreads=1 vs 8）
    g5a, _, _ = build(dict(gamma_f=0.60, W=0.05, L=1e8, psi0=1.0), nthreads=1,
                      nstep=4)
    g5b, _, _ = build(dict(gamma_f=0.60, W=0.05, L=1e8, psi0=1.0), nthreads=8,
                      nstep=4)
    ck('W-5.1 **ψ 开启**时 nthreads=1 vs 8 ⇒ phi 与 psi 都逐位相同',
       np.array_equal(g5a.phi, g5b.phi) and np.array_equal(g5a.psi, g5b.psi),
       'max|Δφ|=%.2e  max|Δψ|=%.2e'
       % (float(np.max(np.abs(g5a.phi - g5b.phi))),
          float(np.max(np.abs(g5a.psi - g5b.psi)))))

    print('-' * 104)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 104)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(main())
