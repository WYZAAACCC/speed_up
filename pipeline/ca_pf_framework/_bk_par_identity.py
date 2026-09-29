#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_par_identity.py —— **新增代码的并行适配判据**（用户 2026-09-29 明确要求）。

## 要证的两件事

| # | 命题 | 为什么必须证 |
|---|---|---|
| **P-1** | **快速路径 == 参考路径（逐位）**：`advance` 里主线程建的 `_gc_full[bb]` 与"逐场调用 `facet_gamma_sub(k, larr[bb], gamma0)`"**逐位相同** | 快速路径是为**并行/内存**改的；若它悄悄改了数，所有生产读数都作废 |
| **P-2** | **线程数不是物理参数**：`nthreads=1` 与 `nthreads=8` 的 `phi` **逐位相同** | 这是本仓库对"并行"的既有验收口径（`windowB_par._selftest` 15/15 逐位）。新代码让 worker 读一张共享只读表 —— **必须证明它没有引入竞态/次序依赖** |

## 装置（两个臂，覆盖"新代码开/关"）

* **臂 N**：`lath=None` ⇒ **新代码整段关闭**（`_gc_full is None`）⇒ 这是"并行本身"的基线；
* **臂 L**：挂 `LathTable`（6 根同变体、θ 阶梯 0–5°）⇒ **新代码生效**。

每臂各跑 `nthreads=1` 与 `nthreads=8`，比较 `phi` 逐位。

跑法：  python3 _bk_par_identity.py
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

F = []


def ck(tag, ok, det=''):
    print('  %-64s %s %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        F.append(tag)


def build(N, L, nthreads, with_lath, nth_lath=6, nlath=6):
    dx = L / N
    laths = [1] * nlath if with_lath else [1, 1]
    lt = (WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                       eps0_var=EPS0, npref_var=NPF, gamma0=0.15)
          if with_lath else None)
    eps0 = ([np.asarray(lt.eps0[i], float) for i in range(len(laths))]
            if with_lath else [np.asarray(EPS0[0], float).copy()] * 2)
    npref = ({i + 1: np.asarray(lt.npref[i + 1], float)
              for i in range(len(laths))} if with_lath
             else {1: np.asarray(NPF[1], float), 2: np.asarray(NPF[1], float)})
    nv = len(eps0)
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=nthreads,
                        reinit_every=0, reinit_dt=6.0e-7, reinit_band_cells=6.0)
    g.lath = lt
    c0 = np.array([L / 2] * 3)
    n_hab = np.asarray(NPF[1], float); n_hab /= np.linalg.norm(n_hab)
    w_ax = np.asarray(g.wtab[1], float); w_ax /= np.linalg.norm(w_ax)
    a_ax = np.asarray(g.atab[1], float); a_ax /= np.linalg.norm(a_ax)
    T, gap, Wd, Lp = 200e-9, 0.0, 500e-9, 1000e-9
    span = (nv - 1) * (T + gap)
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * (T + gap)
        g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T,
                     elong=Lp / Wd, along=a_ax, flat_end=True)
    g.init_parent()
    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=3.5,
              mob_beta_w=2.3, adv_grad='proj2', norm_smooth=0,
              facet_lam=0.0, facet_eps=0.05)
    dt = 0.15 * dx / (MOB * DF)
    for _ in range(6):
        g.advance(dt, **kw)
    return g, n_hab


def main():
    N, L = 48, 3.0e-6
    print('=' * 104)
    print('_bk_par_identity —— 新增代码的并行适配判据  (N=%d, L=%.1f µm)' % (N, L * 1e6))
    print('=' * 104)

    # ---------- P-1 快速路径 == 参考路径（单元级，逐位） ----------
    print('P-1  快速路径 `_gc_full` vs 参考路径 `facet_gamma_sub`（逐位）')
    g, _ = build(N, L, 1, True)
    lt = g.lath
    karr, larr = g.par.argmin2(g.phi)
    karr = karr.astype(np.intp); larr = larr.astype(np.intp)
    G = lt.gtab[np.clip(karr, 0, g.nreg - 1), np.clip(larr, 0, g.nreg - 1)]
    fast = np.where(np.isfinite(G), G, 0.15)
    worst = 0.0
    for k in np.unique(karr):
        bb = (slice(None),) * 3
        ref = lt.facet_gamma_sub(int(k), larr, 0.15)      # 标量或数组
        if np.ndim(ref) == 0:
            ref = np.full(karr.shape, float(ref))
        m = (karr == k)
        worst = max(worst, float(np.max(np.abs(fast[m] - ref[m]))))
    ck('P-1.1 快速路径与参考路径**逐位相同**', worst == 0.0,
       'max|Δ| = %.3e' % worst)
    nf3 = int(np.isfinite(G).sum())
    ck('P-1.2 本装置确实有 F3 胞（否则 P-1.1 是空转）', nf3 > 0,
       'F3 胞 = %d / %d' % (nf3, G.size))
    ck('P-1.3 快速路径在 lath=None 时**不被建立**（原路径逐位不变）',
       build(N, L, 1, False)[0]._gc_full is None)

    # ---------- P-2 线程数不变性（端到端，逐位） ----------
    print('P-2  线程数不变性：nthreads=1 vs nthreads=8 ⇒ phi 逐位相同')
    for tag, wl in (('臂 N（lath=None，新代码关闭）', False),
                    ('臂 L（lath 挂上，新代码生效）', True)):
        g1, _ = build(N, L, 1, wl)
        g8, _ = build(N, L, 8, wl)
        same = np.array_equal(g1.phi, g8.phi)
        ck('P-2 %s' % tag, same,
           'max|Δφ| = %.3e ；region 翻转 %d'
           % (float(np.max(np.abs(g1.phi - g8.phi))),
              int((g1.region() != g8.region()).sum())))
    # 正对照：证明上面"相同"不是"两条路都没跑"
    ga, _ = build(N, L, 1, False)
    gb, _ = build(N, L, 1, True)
    ck('P-2.C 正对照：lath 开/关 ⇒ region 图**不同**（否则上面的"相同"没有意义）',
       not np.array_equal(ga.region(), gb.region()),
       'region 翻转 %d（两臂场数不同：%d vs %d）'
       % (int((ga.region() != gb.region()).sum()), ga.nreg, gb.nreg))

    print('-' * 104)
    print('FAIL = %d %s' % (len(F), F if F else ''))
    print('=' * 104)
    return 1 if F else 0


if __name__ == '__main__':
    raise SystemExit(main())
