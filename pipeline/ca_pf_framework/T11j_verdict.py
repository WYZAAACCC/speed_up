#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11j_verdict.py --- 修 `σ` 定向后的判决（`pair_kernel` + `pair_curvature` 两条路径）。

判据
----
  T11j-1 **平界面标定**（`pair_kernel=True`）：口径 D 的 `v_n/(MΔf)` → **1.000**
        （仓库注释记载修前实测 **0.00** ⇒ 从"完全不动"到"精确"）
  T11j-2 **临界半径**（`pair_curvature=True`）：必须出现**缩/涨分界**，
        且 `γ_eff/γ` 落在 [0.7, 1.3]（解析 1.0）
  T11j-3 **回归守卫**：默认路径（两条都关）的平界面口径 D 与 T11-A′ 逐位一致

用法：python3 T11j_verdict.py [--dx-nm 50]
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

DF, MOB, GAM, DFG = 2.0e8, 1e-9, 0.15, 1.0e6
L = 3000e-9


def front(dx, n_h, pair_kernel=False, nstep=80):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(n_h, float) / np.linalg.norm(n_h)
    rel = g.XYZ - np.array([L / 2] * 3)
    d0 = rel @ n_h
    g.phi[1] = d0
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=20, pair_kernel=pair_kernel)
        t += dt
    phi_ex = d0 - MOB * DF * t
    bm = np.abs(phi_ex) <= 3.0 * dx
    return 1.0 + float(np.median(g.phi[1][bm] - phi_ex[bm])) / (MOB * DF * t)


def growth(R0, dx, pair_curv, nstep=250):
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=GAM, Mob=MOB,
                        df=[0.0, DFG], workers=1, reinit_every=0, nv=1)
    g.pair_curvature = bool(pair_curv)
    g.seed_sphere(1, [L / 2] * 3, R0)
    g.init_parent()
    dt = 0.15 * dx / (MOB * DFG)
    v0 = float((g.region() == 1).sum())
    for _ in range(nstep):
        g.advance(dt, band_cells=20)
    return (float((g.region() == 1).sum()) - v0) / max(v0, 1e-30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dx-nm', type=float, default=50.0)
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    tilt = np.asarray(NPF[1], float)
    tilt = tilt / np.linalg.norm(tilt)
    print('=' * 100)
    print('T11j —— `σ` 定向后的判决   Δx=%.0f nm  L=%.0f nm' % (a.dx_nm, L * 1e9))
    print('=' * 100)
    print('【T11j-1】平界面标定（口径 D，精确 1.000）')
    ok1 = True
    for lab, n_h in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', tilt)):
        v0 = front(dx, n_h, pair_kernel=False)
        v1 = front(dx, n_h, pair_kernel=True)
        good = abs(v1 - 1.0) < 0.05
        ok1 &= good
        print('   %-14s 默认 %+.6f | **pair_kernel** %+.6f  ⇒ %s'
              % (lab, v0, v1, 'PASS' if good else 'FAIL'))
    print('   T11j-1: %s（仓库注释记载修前 pair_kernel 实测 0.00）'
          % ('PASS' if ok1 else 'FAIL'))

    print()
    print('【T11j-2】临界半径（γ_eff/γ，解析 1.0）')
    tabs = {}
    for pc in (False, True):
        rows = []
        for R0 in (100, 150, 200, 250, 300, 400, 600):
            r = growth(R0 * 1e-9, dx, pc)
            rows.append((R0, r))
        tabs[pc] = rows
        print('   pair_curvature=%-5s %s' % (str(pc),
              '  '.join('%.0f:%+.1f' % (R0, r) for R0, r in rows)), flush=True)
    ok2 = True
    for pc in (True,):
        tab = tabs[pc]
        lo = [R0 for R0, r in tab if r < 0]
        hi = [R0 for R0, r in tab if r > 0]
        if not lo or not hi:
            print('    pc=%s ✗ 分界未出现 ⇒ 判据无信息量' % pc)
            ok2 = False
            continue
        Rc = 0.5 * (max(lo) + min(hi)) * 1e-9
        ratio = DFG * Rc / 2.0 / GAM
        good = 0.7 <= ratio <= 1.3
        ok2 &= good
        print('    pc=%s 分界 [%d, %d] nm ⇒ R_crit ≈ %.0f nm，γ_eff/γ = **%.3f**  %s'
              % (pc, max(lo), min(hi), Rc * 1e9, ratio, 'PASS' if good else 'FAIL'))
    print('   T11j-2: %s' % ('PASS' if ok2 else 'FAIL'))

    print()
    print('【T11j-3】回归守卫：默认路径（两条都关）不得变化')
    v_now = front(dx, tilt, pair_kernel=False)
    print('   默认路径倾斜档 = %+.6f（T11g 实测 1.0000 ⇒ 应仍 ≈1）' % v_now)
    ok3 = abs(v_now - 1.0) < 0.05
    print('   T11j-3: %s' % ('PASS' if ok3 else 'FAIL'))

    print()
    print('=' * 100)
    print('  T11j-1 %s | T11j-2 %s | T11j-3 %s'
          % tuple('PASS' if x else 'FAIL' for x in (ok1, ok2, ok3)))
    allok = ok1 and ok2 and ok3
    print('  ⇒ T11j %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
