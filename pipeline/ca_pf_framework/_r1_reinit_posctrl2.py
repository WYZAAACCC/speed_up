#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_posctrl2.py --- R1 reinit 审计（第 4b 步）：Q-C 的**修正版**。

首版（`_r1_reinit_posctrl.py`）的三条读数已归档，但 P1 那一栏**无效**：
`reinit_every=5` 的球生长算例里，**6 个 iters 臂逐位相同** ⇒ 说明 reinit 根本没生效。
两种可能（必须分辨，不能猜）：① `reinit_skip_tol=0.05` 把每一对都跳过了；
② `_finish_advance` 的步数触发没走到。本文件用**计数器**把它判开。

★ 只读引擎；**不改任何引擎代码**。唯一的旋钮是实例属性
  `g.reinit_iters` / `g.reinit_skip_tol`（引擎本来就按这两个属性取值）。

  P1'  **强制 reinit**（`reinit_skip_tol=-1.0` ⇒ `|med−1| ≤ −1` 永不成立 ⇒ 不跳过）：
       球 + 常数驱动、已知答案 `R(t)=R0+v·t`，`reinit_every=5`（生产频率的 ~11 倍）。
  P1'' 同一条轨迹但**默认** `reinit_skip_tol=0.05`：量出到底跳过了多少次（Q-B 的关键）。
  P5  球长 20 步**不 reinit** 后的**退化输入**上，扫 iters ⇒ 量 `带内 median|∇d2|` 的恢复曲线。
"""
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

DF, MOB = 3.5e8, 1e-9
EXACT = MOB * DF
N, DX = 64, 25e-9
L = N * DX
STEPS, EVERY = 60, 5


def bond_count(reg):
    nb = 0
    for ax in range(3):
        nb += int((reg != np.roll(reg, -1, axis=ax)).sum())
    return nb


def sphere_R(g, k=1):
    phi = g.phi[k]
    H = np.clip(0.5 - phi / g.dx, 0.0, 1.0)
    V = float(H.sum()) * g.dx ** 3
    return (3.0 * V / (4.0 * np.pi)) ** (1.0 / 3.0)


def mk(seed_r=0.10, every=EVERY):
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=every)
    R0 = seed_r * L
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    return g, R0


def med_grad_band(d2, dx, band=6.0):
    sel = np.abs(d2) <= band * dx
    if not sel.any():
        return np.nan
    gr = np.gradient(d2, dx, edge_order=2)
    return float(np.median(np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)[sel]))


def P1(force, iters_list):
    tag = 'P1\'(强制,skip_tol=-1)' if force else 'P1\'\'(默认 skip_tol=0.05)'
    print('=' * 116)
    print('%s  球 + 常数驱动，reinit 每 %d 步（生产频率的 ~%.1f 倍）'
          % (tag, EVERY, 6.0e-7 / (EVERY * 0.15 * DX / EXACT)))
    print('  解析 R(t)=R0+v·t，v=%.4f m/s；N=%d Δx=%.0f nm L=%.2f µm R0=%.0f nm'
          % (EXACT, N, DX * 1e9, L * 1e6, 0.10 * L * 1e9))
    print('-' * 116)
    print('  %6s %10s %10s %11s %11s %11s %13s %8s %8s %8s'
          % ('iters', 'R_end(nm)', 'R_ex(nm)', 'R/R_ex−1', '键/干净阶梯',
             '末态med|∇d2|', 'ΣΔR|reinit(nm)', 'done', 'skip', '用时(s)'))
    for n in iters_list:
        t0 = time.time()
        g, R0 = mk()
        g.reinit_iters = n
        if force:
            g.reinit_skip_tol = -1.0
        g._reinit_done = 0
        g._reinit_skipped = 0
        dt = 0.15 * g.dx / EXACT
        t = 0.0
        Rprev = sphere_R(g)
        sumdR = 0.0
        for it in range(1, STEPS + 1):
            g.advance(dt, band_cells=20, adv_grad='proj2')
            t += dt
            R = sphere_R(g)
            if it % EVERY == 0:
                sumdR += R - Rprev - EXACT * dt
            Rprev = R
        Rex = R0 + EXACT * t
        Rj = sphere_R(g)
        ref = 1.5 * 4.0 * np.pi * Rj ** 2 / g.dx ** 2
        print('  %6d %10.2f %10.2f %+11.6f %11.4f %11.5f %+13.4f %8d %8d %8.1f'
              % (n, Rj * 1e9, Rex * 1e9, Rj / Rex - 1.0,
                 bond_count(g.region()) / ref, med_grad_band(g.phi[1], g.dx),
                 sumdR * 1e9, getattr(g, '_reinit_done', 0),
                 getattr(g, '_reinit_skipped', 0), time.time() - t0), flush=True)
        del g


def P5():
    print()
    print('=' * 116)
    print('P5 **退化输入**上的恢复曲线：球长 20 步**不 reinit** 后的 d2，扫 iters')
    print('-' * 116)
    g, R0 = mk(every=0)
    dt = 0.15 * g.dx / EXACT
    for _ in range(20):
        g.advance(dt, band_cells=20, adv_grad='proj2')
    d2 = g.phi[1].copy()
    near = np.abs(d2) <= 6.0 * g.dx
    med_in = med_grad_band(d2, g.dx)
    n0 = int((d2 < 0).sum())
    R0r = sphere_R(g)
    print('  输入：R=%.1f nm  带内 med|∇d2|=%.5f  带胞=%d'
          % (R0r * 1e9, med_in, int(near.sum())))
    print('  %6s %11s %11s %12s %12s %12s %9s'
          % ('iters', 'med_out', '恢复率', 'Δ#{d2<0}', 'Δmed(胞)', 'max|Δ|(胞)', '用时(s)'))
    t0 = time.time()
    for n in (1, 5, 10, 20, 30, 36, 50, 75, 100, 150, 200, 300):
        dn = g.sussman_reinit(d2.copy(), iters=n)
        t1 = time.time() - t0
        t0 = time.time()
        mo = med_grad_band(dn, g.dx)
        print('  %6d %11.5f %10.1f%% %12d %+12.5f %12.5f %9.2f'
              % (n, mo, 100.0 * (mo - med_in) / (1.0 - med_in) if med_in < 1 else 0.0,
                 int((dn < 0).sum()) - n0,
                 (np.median(dn[near]) - np.median(d2[near])) / g.dx,
                 float(np.max(np.abs(dn[near] - d2[near]))) / g.dx, t1), flush=True)
    del g


def main():
    print('#' * 116)
    print('R1 reinit 审计 / Q-C 修正版   首版 P1 无效的原因判读 + 强制 reinit 的对照')
    print('#' * 116)
    P1(False, [100])
    P1(True, [1, 10, 20, 36, 50, 100, 150])
    P5()
    print('=' * 116)
    return 0


if __name__ == '__main__':
    sys.exit(main())
