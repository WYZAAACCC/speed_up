#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_identity.py --- R30 审计 S1：**线程数不是物理参数**的独立复核。

不依赖 `windowB_par._selftest`（它只测算子），本脚本做**端到端**判据：

  [A] `windowB_par._selftest(N=64, nthreads=4)` —— 仓库自带算子级判据（照跑并报告）
  [B] 端到端：同一初值、同一 `dt`、同一 kwargs，只改 `g.par.n` ∈ {1,2,4}
      ⇒ `phi`（以及开启时的 `psi`）必须**逐位相同**
  [C] **正对照**（应逐位相同）：只改 `g.par.min_rows`（1,2,3）—— 只改**分段方式**，
      不改任何数值 ⇒ 逐位相同。这证明"分段粒度"本身不是隐藏物理参数。
  [D] **负对照**（必须不同）：`dt ← dt·(1+1e-12)` ⇒ `phi` 必须不同。
      ⇒ 证明 [B]/[C] 的"相同"不是量具失灵（比较器有分辨力）。
  [E] 比较器分辨率自证：对同一个 `phi` 的拷贝改 **1 ULP** ⇒ 比较器必须报"不同"。
  [F] 覆盖自证：打印 `g.par.stats`，证明**并行路径确实被走到**（nth_max>1），
      否则 [B] 的"相同"是平凡相同（两条路都没并行）。

用法：python3 -u _r30_identity.py [N] [nsteps] [film 0/1]
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 64
NSTEP = int(sys.argv[2]) if len(sys.argv) > 2 else 3
USE_FILM = (int(sys.argv[3]) if len(sys.argv) > 3 else 0) == 1
DX = 125e-9
GAMMA0 = 0.25
NLATH = 11
REINIT_ITERS = 20          # 只为把 reinit 压到可跑；并行路径与默认 100 完全相同
REINIT_DT = 1.0e-7
F = []


def ck(tag, ok, det=''):
    print('  %-62s %s   %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def bit_same(a, b):
    return (a.dtype == b.dtype) and np.array_equal(
        np.ascontiguousarray(a).view(np.uint8),
        np.ascontiguousarray(b).view(np.uint8))


def build(N):
    L = N * DX
    laths = [1] * NLATH
    lt = WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                      eps0_var=EPS0, npref_var=NPF, gamma0=GAMMA0)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(len(laths))]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float)
             for i in range(len(laths))}
    nv = len(eps0)
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=GAMMA0, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=1, reinit_every=0,
                        reinit_dt=REINIT_DT, reinit_band_cells=6.0,
                        reinit_iters=REINIT_ITERS)
    g.lath = lt
    if USE_FILM:
        g.film = dict(gamma_f=0.60, W=0.05, L=1.0e8, psi0=0.99)
    c0 = np.array([L / 2] * 3)
    n_hab = np.asarray(NPF[1], float)
    n_hab /= np.linalg.norm(n_hab)
    a_ax = np.asarray(g.atab[1], float)
    a_ax /= np.linalg.norm(a_ax)
    T, gap, Wd, Lp = 3 * DX, 0.0, 8 * DX, 20 * DX
    ns = 0
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * (T + gap)
        try:
            g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T,
                         elong=Lp / Wd, along=a_ax, flat_end=True)
            ns += 1
        except ValueError:
            pass
    g.init_parent()
    print('  装置：N=%d L=%.2f µm  播片 %d/%d  活跃区域 %s  film=%s'
          % (N, L * 1e6, ns, nv, np.unique(g.region()).tolist(), USE_FILM))
    return g, npref


def run(g, npref, dt, nstep, nth=None, min_rows=None, dt_scale=1.0):
    """从**同一初值**重跑 nstep 步（调用方负责恢复初值）。"""
    if nth is not None:
        g.par.set_threads(nth)
    if min_rows is not None:
        g.par.min_rows = min_rows
    g.par.stats = {}
    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5,
              mob_beta_w=2.3, adv_grad='proj2', norm_smooth=0,
              facet_lam=0.0, facet_eps=0.05)
    for _ in range(nstep):
        g.advance(dt * dt_scale, **kw)
    return g.phi.copy(), (None if g.psi is None else g.psi.copy()), \
        {k: (v[1], v[2]) for k, v in g.par.stats.items()}


def main():
    print('=' * 104)
    print('_r30_identity   N=%d  步数=%d  film=%d' % (N, NSTEP, USE_FILM))
    print('=' * 104)

    # ---------------- [A] 仓库自带算子级自检 ----------------
    print('[A] windowB_par._selftest(N=64, nthreads=4)')
    import windowB_par as WP
    okA = WP._selftest(64, 4)
    print('')

    # ---------------- [B][C][D][E] 端到端 ----------------
    g, npref = build(N)
    dt = 0.15 * g.dx / (MOB * DF)
    phi0 = g.phi.copy()
    psi0 = None if g.psi is None else g.psi.copy()
    t0 = g._t_since_reinit
    print('  dt = %.4e s；g.par.n(构造) = %d' % (dt, g.par.n))

    def restore():
        g.phi[:] = phi0
        g.psi = None if psi0 is None else psi0.copy()
        g._t_since_reinit = t0
        g._need_reinit = False

    print('\n[B] 端到端：只改线程数 ⇒ phi 必须逐位相同')
    ref = None
    for nth in (1, 2, 4):
        restore()
        p, ps, st = run(g, npref, dt, NSTEP, nth=nth, min_rows=2)
        if ref is None:
            ref, ref_ps, ref_st = p, ps, st
            ck('B-0 覆盖自证：workers=1 时并行算子不启用（nth_max 全 =1）',
               all(v[1] == 1 for v in st.values()),
               'tags=%d' % len(st))
        else:
            ck('B workers=1 vs %d：phi 逐位相同' % nth, bit_same(ref, p),
               'max|Δφ| = %.3e' % float(np.max(np.abs(ref - p))))
            if ps is not None and ref_ps is not None:
                ck('B workers=1 vs %d：psi 逐位相同' % nth,
                   bit_same(ref_ps, ps),
                   'max|Δψ| = %.3e' % float(np.max(np.abs(ref_ps - ps))))
        print('      workers=%d 的并行算子实际分段（tag: 次数, nth_max）: %s'
              % (nth, {k: v for k, v in st.items() if v[1] > 1} or '（无）'))
    ck('B-1 覆盖自证：workers=4 时至少有算子真的分段（否则上面的"相同"是平凡相同）',
       any(v[1] > 1 for v in st.values()),
       'nth_max>1 的 tag: %s' % sorted(k for k, v in st.items() if v[1] > 1))

    print('\n[C] 正对照（应逐位相同）：只改分段粒度 g.par.min_rows')
    for mr in (1, 3):
        restore()
        p, _, st = run(g, npref, dt, NSTEP, nth=4, min_rows=mr)
        ck('C workers=4, min_rows=%d vs 2：phi 逐位相同' % mr, bit_same(ref, p),
           'max|Δφ| = %.3e ; nth_max 分布 %s'
           % (float(np.max(np.abs(ref - p))),
              sorted(set(v[1] for v in st.values()))))

    print('\n[D] 负对照（必须不同）：dt ← dt·(1+1e-12)')
    restore()
    p, _, _ = run(g, npref, dt, NSTEP, nth=4, min_rows=2, dt_scale=1.0 + 1e-12)
    ck('D dt 改 1e-12 相对量 ⇒ phi **不同**（量具有分辨力）',
       not bit_same(ref, p),
       'max|Δφ| = %.3e' % float(np.max(np.abs(ref - p))))

    print('\n[E] 比较器分辨率自证：把拷贝的 1 个元素改 1 ULP')
    q = ref.copy()
    q.ravel()[0] = np.nextafter(q.ravel()[0], np.inf)
    ck('E 1 ULP 扰动必须被判为"不同"', not bit_same(ref, q))

    print('-' * 104)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 104)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(main())
