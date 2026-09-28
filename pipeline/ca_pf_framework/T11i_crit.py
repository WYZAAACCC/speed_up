#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11i_crit.py --- 用**临界半径**量 γ_eff（修正 T11h 的实验设计错误）。

为什么 T11h 的测法无效（记账）
-----------------------------
`v = M(Δf − 2γ/R)` ⇒ `R_eq = 2γ/Δf` 是**不稳定平衡**：`R < R_eq` 缩、`R > R_eq` 涨。
从 `R0 = 400 nm > R_eq = 300 nm` 起跑**必然跑飞**，读到的 R_eq 是"盒子尺寸"而不是平衡半径。
⇒ 正确量法：**扫 R0 找"缩/涨"的分界**，那个分界就是临界半径 `R_crit = 2γ/Δf`
⇒ `γ_eff = Δf·R_crit/2`。

判据
----
  T11i-1 `γ_eff/γ → 1`（判据 |比值−1| < 0.30），对比 `pair_curvature` 关/开
  T11i-2 分界必须**真的出现**（低 R0 缩、高 R0 涨）——否则判据无信息量

用法：python3 T11i_crit.py [--dx-nm 50] [--r0s 100,150,200,300,400,600]
"""
import os
import sys
import argparse

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

MOB, GAM, DFG = 1e-9, 0.15, 1.0e6
L = 3000e-9
R_CRIT_EXACT = 2 * GAM / DFG          # = 300 nm


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
    v1 = float((g.region() == 1).sum())
    return (v1 - v0) / max(v0, 1e-30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dx-nm', type=float, default=50.0)
    ap.add_argument('--r0s', type=str, default='100,150,200,250,300,400,600')
    a = ap.parse_args()
    dx = a.dx_nm * 1e-9
    r0s = [float(x) * 1e-9 for x in a.r0s.split(',')]
    print('=' * 100)
    print('T11i —— 临界半径量 γ_eff   Δx=%.0f nm  L=%.0f nm' % (a.dx_nm, L * 1e9))
    print('  解析临界半径 R_crit = 2γ/Δf = %.1f nm ⇒ γ_eff = Δf·R_crit/2' % (R_CRIT_EXACT * 1e9))
    print('=' * 100)
    print('%-8s | %s' % ('R0(nm)', '   '.join('pc=%-5s' % p for p in ('False', 'True'))))
    tabs = {False: [], True: []}
    for R0 in r0s:
        row = []
        for pc in (False, True):
            r = growth(R0, dx, pc)
            tabs[pc].append((R0, r))
            row.append('%+.4f' % r)
        print('%-8.0f | %s' % (R0 * 1e9, '   '.join(row)), flush=True)
    print()
    print('  判据 T11i-2（分界必须出现）与 T11i-1（γ_eff/γ → 1）：')
    okall = True
    for pc in (False, True):
        tab = tabs[pc]
        low = [r for R0, r in tab if r < 0]
        high = [r for R0, r in tab if r > 0]
        if not low or not high:
            print('    pc=%-5s ✗ 分界未出现（全%s）⇒ 判据无信息量'
                  % (str(pc), '缩' if not high else '涨'))
            okall = False
            continue
        # 分界夹在 max(缩) 与 min(涨) 之间
        r_lo = max(R0 for R0, r in tab if r < 0)
        r_hi = min(R0 for R0, r in tab if r > 0)
        Rc = 0.5 * (r_lo + r_hi)
        gam_eff = DFG * Rc / 2.0
        ratio = gam_eff / GAM
        ok = abs(ratio - 1.0) < 0.30
        okall &= ok
        print('    pc=%-5s 分界落在 [%.0f, %.0f] nm ⇒ R_crit ≈ %.0f nm，'
              'γ_eff/γ = **%.3f**  %s'
              % (str(pc), r_lo * 1e9, r_hi * 1e9, Rc * 1e9, ratio,
                 'PASS' if ok else 'FAIL'))
    print()
    print('  ⇒ T11i %s' % ('PASS' if okall else 'FAIL'))
    print('=' * 100)
    return 0 if okall else 1


if __name__ == '__main__':
    sys.exit(main())
