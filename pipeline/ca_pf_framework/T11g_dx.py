#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11g_dx.py --- T11 修正版判据（用**无偏口径**重测 Δx 无关性）。

为什么会重写（T11f 的更正）
--------------------------
前几轮用 `iface_offset`（沿固定盒轴求 φ 的亚胞零交点再平均）量前沿位移，
它在**倾斜/阶梯前沿**上系统性低估位移（实测报 37% 赤字，而零插值真值只有 1e-4 %）。
⇒ 那把尺子对倾斜前沿**有偏**。本脚本换两把**无偏**的尺子：

  **E 体积分数**（整数计数、零插值）：
      周期盒里平面 `n·x = c` 每周期只有一张面片，其面积 `A = L²/|n_z|`（任一 `n_z≠0` 的轴）
      ⇒ 平面沿 n 平移 δ 扫过体积 `A·δ` ⇒ **`δ = Δf_vol · L · |n_axis|`**（精确关系，只对平面）
  **D 残差常值**（★ 真值对照）：`φ_exact = n·(x−x0) − v·t`；
      `rel_err = −median(φ_1 − φ_exact)/(v·t)`

判断
----
  T11-A′ 平面前沿速度：E 与 D **都要** <5% 误差，且三档 Δx 的相对散布 <5%
  T11-B  界面面积测度（`cell_area_geom`，与上述偏无关）随 Δx 收敛
  T11-C  Gibbs–Thomson `γ_eff`（体积口径，无偏）：可分辨工况下三档 Δx 散布 <10%

用法：python3 T11g_dx.py [--L-nm 3000] [--dxs 40,50,62.5]
退出码：0 = PASS
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn

DF, MOB = 2.0e8, 1e-9
EXACT = MOB * DF


def plane_front(L, N, dx, n_h, nstep=80, band=20):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(n_h, float) / np.linalg.norm(n_h)
    ax = int(np.argmax(np.abs(n_h)))
    rel = g.XYZ - np.array([L / 2] * 3)
    d0 = rel @ n_h
    g.phi[1] = d0
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / EXACT
    f0 = float((g.phi[1] < 0).sum()) / g.N ** 3
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=band)
        t += dt
    f1 = float((g.phi[1] < 0).sum()) / g.N ** 3
    # E：体积口径（无偏，仅对平面成立）
    dE = (f1 - f0) * L * abs(n_h[ax])
    vE = dE / t / EXACT
    # D：零插值真值（残差）
    phi_ex = d0 - EXACT * t
    bm = np.abs(phi_ex) <= 3.0 * dx
    resid = g.phi[1][bm] - phi_ex[bm]
    vD = 1.0 + float(np.median(resid)) / (EXACT * t)
    return vE, vD


def dx_scan(L, dxs, fn, lab):
    rows = []
    for dx in dxs:
        N = int(round(L / dx))
        r = fn(N, dx)
        rows.append((dx, r))
        print('   %-22s Δx=%-7.1f nm (N=%-4d) ⇒ %s'
              % (lab, dx * 1e9, N, '  '.join('%.4f' % x for x in r)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    tilt = np.asarray(NPF[1], float)
    tilt = tilt / np.linalg.norm(tilt)
    print('=' * 100)
    print('T11g —— 无偏口径重测 Δx 无关性   L=%.0f nm  Δx=%s nm' % (a.L_nm, a.dxs))
    print('  E = 体积口径（无偏，平面精确）; D = 零插值真值。两者都应是 1.000')
    print('=' * 100)

    print('【T11-A′】平面前沿速度')
    res = {}
    for lab, n_h in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', tilt)):
        rows = dx_scan(L, dxs, lambda N, dx, n=n_h: plane_front(L, N, dx, n), lab)
        res[lab] = rows
    okA = True
    for lab, rows in res.items():
        for i, nm in ((0, 'E'), (1, 'D')):
            v = np.array([r[1][i] for r in rows], float)
            sp = float((v.max() - v.min()) / abs(v.mean()))
            err = float(np.max(np.abs(v - 1.0)))
            good = (sp < 0.05) and (err < 0.05)
            okA &= good
            print('    %-14s 口径 %s：均值 %.4f 最大偏差 %.2f%% 散布 %.4f  %s'
                  % (lab, nm, v.mean(), 100 * err, sp, 'OK' if good else '✗'))
    print('   T11-A′: %s' % ('PASS' if okA else 'FAIL'))

    print()
    print('【T11-B】界面面积测度（解析球 R=0.25L）——与上述偏无关')
    ab = []
    for dx in dxs:
        N = int(round(L / dx))
        R = 0.25 * L
        g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                            df=[0.0, 1e8], workers=1, reinit_every=0, nv=1)
        g.seed_sphere(1, [L / 2] * 3, R)
        g.init_parent()
        A = float(g.cell_area_geom().sum())
        ab.append(A / (4 * np.pi * R ** 2))
        print('   Δx=%-7.1f nm (N=%-4d)  A/A_exact = %.4f（%+.2f%%）'
              % (dx * 1e9, N, ab[-1], 100 * (ab[-1] - 1)))
    okB = bool(np.max(np.abs(np.array(ab) - 1.0)) < 0.05)
    print('   T11-B: %s（判据：偏差 <5%%）' % ('PASS' if okB else 'FAIL'))

    print()
    print('【T11-C】Gibbs–Thomson γ_eff（体积口径，可分辨工况 Δf=1e6 ⇒ R_eq≈300 nm）')
    gc = []
    for dx in dxs:
        N = int(round(L / dx))
        DFg = 1.0e6
        g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=MOB,
                            df=[0.0, DFg], workers=1, reinit_every=0, nv=1)
        R0 = 0.1333 * L                       # 400 nm：从 R_eq 两侧收敛
        g.seed_sphere(1, [L / 2] * 3, R0)
        g.init_parent()
        dt = 0.15 * dx / (MOB * DFg)
        vs = []
        for it in range(2000):
            g.advance(dt, band_cells=20)
            if (it + 1) % 200 == 0:
                vs.append(float((g.region() == 1).sum()))
        conv = abs(vs[-1] - vs[-2]) / max(vs[-2], 1e-30)
        V = vs[-1] * dx ** 3
        Req = (3.0 * V / (4.0 * np.pi)) ** (1.0 / 3.0)
        gc.append(DFg * Req / 2.0)
        print('   Δx=%-7.1f nm  R_eq = %.2f nm  γ_eff = %.5e J/m²（输入 γ=0.15）'
              '  末段体积变化 %.2e' % (dx * 1e9, Req * 1e9, gc[-1], conv))
    gc = np.array(gc)
    spC = float((gc.max() - gc.min()) / abs(gc.mean()))
    errC = float(np.max(np.abs(gc / 0.15 - 1.0)))
    okC = (spC < 0.10) and (errC < 0.30)
    print('   散布 %.4f（<0.10）；与输入 γ 的最大偏差 %.1f%%（<30%%）' % (spC, 100 * errC))
    print('   T11-C: %s' % ('PASS' if okC else 'FAIL'))

    print()
    print('=' * 100)
    print('  T11-A′ %s | T11-B %s | T11-C %s'
          % tuple('PASS' if x else 'FAIL' for x in (okA, okB, okC)))
    allok = okA and okB and okC
    print('  ⇒ T11（修正版）%s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
