#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_posctrl.py --- R1 reinit 审计（第 4 步）：**Q-C 已知答案正对照**。

★ 只读引擎；**不改任何引擎代码**。

四个测试（全部是**已知答案**，量具沿用 T19 已验证的 `sphere_R`（coarea 部分体积）
与 `bond_count`，干净阶梯基准 `1.5·4πR²/Δx²`）：

 P1 **球 + 常数驱动**（`nv=1`、`gamma=0`、`C=None` ⇒ 弹性能恒 0）：
    解析解 `R(t) = R0 + v·t`，`v = M·Δf`。`reinit_every=5` 是**生产频率的 ~11 倍**
    （生产中 Δx=25nm 时 `reinit_dt=6e-7` ⇒ 每 56 步）⇒ **故意放大 reinit 的影响**。
    扫 `reinit_iters ∈ {1,10,20,36,50,100}`，量末态 `R/R_ex−1`、`键/干净阶梯`、
    以及**每次 reinit 造成的 ΔR**（= reinit 动界面的直接读数）。

 P2 **纯 reinit 不动点**（不推进）：解析 SDF 球连做 5 次 reinit，R 必须**不变**
    （SDF 是 Sussman 的不动点）。扫 iters。（隔离"迭代不足"这一个因素。）

 P3 **量具负对照**：把 `2·d2`（= `d`，即 P0-3 那个"目标 |∇d|=1 而非 2"的**错**写法）
    喂给 reinit，量具**必须**读出 `med|∇d2|→0.5` 与大幅界面位移；恒等算子必须读 0。
    ⇒ 证明量具不是瞎的。

 P4 **完美 SDF 的平界面**（`nv=2`，无母相，`φ1 = z−z0`、`φ2 = −(z−z0)`）：
    d2 本身就是精确 SDF ⇒ 任何 iters 都必须是 no-op（**负对照**：
    说明 P1/P2 里的差异来自"输入不是 SDF"，不是来自量具噪声）。
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
ITERS = [1, 10, 20, 36, 50, 100]
NSPH, DXSPH = 64, 25e-9
NPL, DXPL = 48, 25e-9
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


def mk_sphere(N=NSPH, dx=DXSPH, R0f=0.10, every=0):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.0, Mob=MOB,
                        df=[0.0, DF], workers=1, reinit_every=every)
    R0 = R0f * L
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    return g, R0


def med_grad_band(d2, dx, band=6.0):
    sel = np.abs(d2) <= band * dx
    if not sel.any():
        return np.nan
    gr = np.gradient(d2, dx, edge_order=2)
    gn = np.sqrt(gr[0] ** 2 + gr[1] ** 2 + gr[2] ** 2)
    return float(np.median(gn[sel]))


# ------------------------------------------------------------------ P1
def P1():
    print('=' * 112)
    print('P1 球 + 常数驱动（解析 R(t)=R0+v·t，v=M·Δf=%.3f m/s）；'
          'reinit 每 %d 步（生产频率的 ~%.0f 倍）'
          % (EXACT, EVERY, 6.0e-7 / (EVERY * 0.15 * DXSPH / EXACT)))
    print('   N=%d Δx=%.0f nm L=%.2f µm R0=%.0f nm  判据 T19-D：|R/R_ex−1| < 2%%；'
          'T19-C：键/干净阶梯 < 1.15'
          % (NSPH, DXSPH * 1e9, NSPH * DXSPH * 1e6, 0.10 * NSPH * DXSPH * 1e9))
    print('-' * 112)
    print('  %6s %10s %10s %11s %11s %11s %12s %10s'
          % ('iters', 'R_end(nm)', 'R_ex(nm)', 'R/R_ex−1', '键/干净阶梯',
             '末态med|∇d2|', 'ΣΔR|reinit', '用时(s)'))
    rows = []
    for n in ITERS:
        t0 = time.time()
        g, R0 = mk_sphere(every=EVERY)
        g.reinit_iters = n
        dt = 0.15 * g.dx / EXACT
        t = 0.0
        Rprev = sphere_R(g)
        sumdR = 0.0
        nb_end = 0
        for it in range(1, STEPS + 1):
            g.advance(dt, band_cells=20, adv_grad='proj2')
            t += dt
            R = sphere_R(g)
            if it % EVERY == 0:                     # 本步内发生了 reinit
                sumdR += R - Rprev - EXACT * dt
            Rprev = R
            if it == STEPS:
                nb_end = bond_count(g.region())
        Rex = R0 + EXACT * t
        Rj = sphere_R(g)
        ref = 1.5 * 4.0 * np.pi * Rj ** 2 / g.dx ** 2
        d2 = g.phi[1]
        med = med_grad_band(d2, g.dx)
        print('  %6d %10.1f %10.1f %+11.5f %11.3f %11.4f %+12.4f %10.1f'
              % (n, Rj * 1e9, Rex * 1e9, Rj / Rex - 1.0, nb_end / ref, med,
                 sumdR * 1e9, time.time() - t0), flush=True)
        rows.append((n, Rj / Rex - 1.0, nb_end / ref, med, sumdR * 1e9))
        del g
    print('  ⇒ 量具分辨力自检：iters=1 与 iters=100 的 (R/R_ex−1) 之差 = %.5f'
          % abs(rows[0][1] - rows[-1][1]))
    return rows


# ------------------------------------------------------------------ P2
def P2():
    print()
    print('=' * 112)
    print('P2 纯 reinit 不动点：解析 SDF 球**不推进**，连做 5 次 reinit，R 必须不变')
    print('-' * 112)
    print('  %6s %12s %12s %12s %12s %12s %12s'
          % ('iters', 'R0(nm)', 'R1', 'R2', 'R3', 'R4', 'R5'))
    for n in ITERS:
        g, R0 = mk_sphere(every=0)
        g.reinit_iters = n
        Rs = [sphere_R(g)]
        for _ in range(5):
            d2 = g.phi[1]
            dn = g.sussman_reinit(d2, iters=n)
            g.phi[1] = dn
            g.phi[0] = -dn
            Rs.append(sphere_R(g))
        print('  %6d %12.3f %12.3f %12.3f %12.3f %12.3f %12.3f'
              % (n, Rs[0] * 1e9, Rs[1] * 1e9, Rs[2] * 1e9, Rs[3] * 1e9,
                 Rs[4] * 1e9, Rs[5] * 1e9), flush=True)
        print('         ⇒ 累计 ΔR = %+.4f nm （%.4f 胞）'
              % ((Rs[5] - Rs[0]) * 1e9, (Rs[5] - Rs[0]) / g.dx), flush=True)
        del g


# ------------------------------------------------------------------ P3
def P3():
    print()
    print('=' * 112)
    print('P3 量具负对照：恒等算子 / 故意喂错目标（2·d2，即 P0-3 的错写法，目标 |∇d|=1）')
    print('-' * 112)
    g, R0 = mk_sphere(every=0)
    d2 = g.phi[1]
    near = np.abs(d2) <= 6.0 * g.dx
    med0 = med_grad_band(d2, g.dx)
    nneg0 = int((d2 < 0).sum())
    # (a) 恒等算子（恒等 ⇒ Δ 必须**精确为 0**）
    did = d2.copy()
    print('  (a) 恒等        ：med=%.5f  Δ#{d2<0}=%+d  max|Δ|/dx=%.3e'
          % (med_grad_band(did, g.dx), int((did < 0).sum()) - nneg0,
             float(np.max(np.abs(did - d2))) / g.dx))
    # (b) 错目标：对 2·d2 做 reinit，再当 d2 写回
    bad = g.sussman_reinit(2.0 * d2.copy(), iters=100)
    print('  (b) 喂 2·d2 后回写：med=%.5f  Δ#{d2<0}=%+d  max|Δ|/dx=%.3e  '
          'flips=%d  ⇒ 量具**能**分辨（med 应→~0.5，Δ 应大）'
          % (med_grad_band(bad, g.dx), int((bad < 0).sum()) - nneg0,
             float(np.max(np.abs(bad - d2))) / g.dx,
             int((np.where(d2 < 0, 0, 1) != np.where(bad < 0, 0, 1)).sum())))
    # (c) 正确路径 iters=100（应≈不动点）
    good = g.sussman_reinit(d2.copy(), iters=100)
    print('  (c) 正确 d2/1  ：med=%.5f  Δ#{d2<0}=%+d  max|Δ|/dx=%.3e'
          % (med_grad_band(good, g.dx), int((good < 0).sum()) - nneg0,
             float(np.max(np.abs(good - d2))) / g.dx))
    print('      输入态 med=%.5f（初值）' % med0)
    del g


# ------------------------------------------------------------------ P4
def P4():
    print()
    print('=' * 112)
    print('P4 负对照：**完美线性 SDF** 的平界面（nv=2，无母相）—— 任何 iters 都必须是 no-op')
    print('-' * 112)
    N, dx = NPL, DXPL
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=2, gamma=0.0, Mob=MOB,
                        df=[0.0, DF, 0.0], workers=1, reinit_every=0)
    z = (np.arange(N) + 0.5) * dx
    d = z[None, None, :] - 0.5 * L
    g.phi[0] = 1e3
    g.phi[1] = np.broadcast_to(d, (N, N, N)).copy()
    g.phi[2] = -g.phi[1]
    d2 = 0.5 * (g.phi[1] - g.phi[2])
    near = np.abs(d2) <= 6.0 * dx
    nneg0 = int((d2 < 0).sum())
    print('  %6s %10s %10s %12s %12s' % ('iters', 'med_in', 'med_out',
                                         'Δ#{d2<0}', 'max|Δ|/dx'))
    for n in ITERS:
        dn = g.sussman_reinit(d2.copy(), iters=n)
        print('  %6d %10.6f %10.6f %12d %12.3e'
              % (n, med_grad_band(d2, dx), med_grad_band(dn, dx),
                 int((dn < 0).sum()) - nneg0,
                 float(np.max(np.abs(dn - d2))) / dx), flush=True)
    del g


def main():
    print('#' * 112)
    print('R1 reinit 审计 / Q-C 已知答案正对照   Δf=%.2e J/m³  M=%.1e ⇒ v_exact=%.4f m/s'
          % (DF, MOB, EXACT))
    print('#' * 112)
    P2()
    P3()
    P4()
    P1()
    print()
    print('=' * 112)
    return 0


if __name__ == '__main__':
    sys.exit(main())
