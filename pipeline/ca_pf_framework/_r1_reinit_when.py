#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_when.py --- R1 reinit 审计（第 9 步）：**生产路径上 reinit 到底跑没跑**。

为什么这一条最关键
------------------
归档把"一次 reinit ≈ 16 个普通步"折算成 **"reinit 占 N=96 单步成本的 74%"**。
但那个 16× 是**第 6 步**那一次（撒核后的第一次，`_med` 远离 1 ⇒ **不会**被跳过）。
而 `reinitialize()` 有 `reinit_skip_tol=0.05` 的跳过判据 ——
**若后续每一次都被跳过，那 74% 就是一次性成本，不是稳态成本**，
"降低 reinit_iters" 这件事在整个生产跑里的收益就要重算。

本文件直接实测（★ 只读引擎，不改任何引擎代码）：
  臂 A（生产默认）  ：`reinit_dt=6e-7`、`reinit_skip_tol=0.05`、`reinit_iters=100`
  臂 B（反事实）    ：同上但 `reinit_skip_tol=-1`（永不跳过）—— 量"如果每次都真跑"要多少钱
逐事件记录：步时、`_reinit_done` / `_reinit_skipped` 增量、最大配对的带内中位 |∇d2|。
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
BAND = 6.0
REINIT_DT = 6.0e-7


def gcen(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def active_pairs(reg):
    pairs = set()
    for ax in range(3):
        a = reg
        b = np.roll(reg, -1, axis=ax)
        sel = a != b
        if sel.any():
            for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                if x != y:
                    pairs.add((int(min(x, y)), int(max(x, y))))
    return sorted(pairs)


def worst_med(g):
    reg = g.region()
    worst, mx = 9.9, -1
    for (k, l) in active_pairs(reg):
        d2 = 0.5 * (g.phi[k] - g.phi[l])
        near = np.abs(d2) <= BAND * g.dx
        if not near.any():
            continue
        m = float(np.median(gcen(d2, g.dx)[near]))
        if abs(m - 1.0) > mx:
            mx = abs(m - 1.0)
            worst = m
    return worst, len(active_pairs(reg))


def build(skip_tol):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.15, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0,
                        reinit_dt=REINIT_DT, reinit_band_cells=BAND,
                        reinit_iters=100)
    if skip_tol is not None:
        g.reinit_skip_tol = skip_tol
    rng = np.random.default_rng(7)
    st = L / 2.0
    ns = 0
    for i in range(2):
        for j in range(2):
            for k in range(2):
                c = (np.array([i + 0.5, j + 0.5, k + 0.5]) * st
                     + (rng.random(3) - 0.5) * 0.25 * st)
                kk = ns + 1
                nrm = np.asarray(NPF[kk], float)
                g.seed_plate(kk, c, nrm / np.linalg.norm(nrm), 1.5e-6, 0.9e-6)
                ns += 1
    g.init_parent()
    return g


def arm(tag, skip_tol, nstep):
    print()
    print('  ================= 臂 %s ：skip_tol=%s，%d 步 ================='
          % (tag, skip_tol, nstep), flush=True)
    g = build(skip_tol)
    dt = 0.15 * DX / (MOB * DF)
    print('  %5s %10s %8s %8s %8s %7s %11s %11s'
          % ('step', '步时(s)', 'doneΔ', 'skipΔ', '配对数', '触发', '最差med', '累计(s)'))
    t_all = time.time()
    t_re = 0.0
    n_re = 0
    t_norm = []
    for it in range(1, nstep + 1):
        d0 = getattr(g, '_reinit_done', 0)
        s0 = getattr(g, '_reinit_skipped', 0)
        t0 = time.time()
        g.elastic_driving()
        g.advance(dt, aniso=0.4, npref=NPF, band_cells=20,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
        el = time.time() - t0
        fired = (getattr(g, '_t_since_reinit', 1.0) == 0.0)
        dd = getattr(g, '_reinit_done', 0) - d0
        sd = getattr(g, '_reinit_skipped', 0) - s0
        if fired:
            n_re += 1
            t_re += el
            wm, np_ = worst_med(g)
            print('  %5d %10.2f %8d %8d %8d %7s %11.5f %11.1f'
                  % (it, el, dd, sd, np_, 'YES', wm, time.time() - t_all), flush=True)
        else:
            t_norm.append(el)
            if it % 20 == 0:
                print('  %5d %10.2f %8s %8s %8s %7s %11s %11.1f'
                      % (it, el, '-', '-', '-', '-', '-', time.time() - t_all),
                      flush=True)
    tot = time.time() - t_all
    if t_norm:
        print('  ⇒ 臂 %s 汇总：总 %.1f s（%.2f s/步）  reinit 事件 %d 次，'
              '落在 reinit 步上的时间 %.1f s = **%.1f%%**；普通步均值 %.2f s'
              % (tag, tot, tot / nstep, n_re, t_re, 100 * t_re / tot,
                 float(np.mean(t_norm))), flush=True)
    else:
        print('  ⇒ 臂 %s 汇总：总 %.1f s  reinit 事件 %d 次，时间 %.1f s'
              % (tag, tot, n_re, t_re), flush=True)
    del g


def main():
    print('=' * 122)
    print('R1 reinit 审计 / 生产触发口径下 reinit 到底跑没跑（done vs skip）')
    print('  N=%d Δx=%.0f nm L=%.1f µm  8 个核（8 变体）  reinit_dt=%.1e s  dt=%.4e s'
          % (N, DX * 1e9, L * 1e6, REINIT_DT, 0.15 * DX / (MOB * DF)))
    print('  触发间隔 = %.2f 步' % (REINIT_DT / (0.15 * DX / (MOB * DF))))
    print('=' * 122)
    arm('A 生产默认', 0.05, 40)
    arm('B 反事实(永不跳过)', -1.0, 14)
    print()
    print('=' * 122)
    return 0


if __name__ == '__main__':
    sys.exit(main())
