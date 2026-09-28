#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11b_isolate.py --- T11 后续：**定位 Δx 依赖的来源**（只查"怎么算"，不改"算什么"）。

★ 先修一处判据错误（记账）
--------------------------
`T11_verify_dx.py::t11_A` 量的是**沿盒轴**的界面位移 `dz/dt`，而界面法向 `n_h` 是**斜的**
⇒ 正确关系是 `dz/dt = v_n / |n_axis|`（平面 `n·x = const` 推进 v_n）。
首版直接拿 `dz/dt` 比 `M·Δf`，**漏了 `1/n_z`** ⇒ 报出的"比值"其实是 `v_n/(n_z·MΔf)`，
把赤字**看小了**（实测 ~0.85，真值 ~0.85/n_z≈0.66）。

隔离矩阵（固定 L=3000 nm，Δx = 40/50/62.5 nm，γ=0、Δf 常数 ⇒ 精确解 v_n = M·Δf）
-----------------------------------------------------------------------------
逐项只改一个因素：
  · `adv_grad` ∈ {central, upwind}
  · `extend`   ∈ {edt, None}      （速度延拓 vs 只在界面胞给速度）
  · `band`     ∈ {物理 1000 nm, 20 胞}
输出每个组合的三档 `v_n/(MΔf)` 与相对散布，指出**哪个因素主导** Δx 依赖。

用法：python3 T11b_isolate.py [--L-nm 3000] [--dxs 40,50,62.5]
"""
import os
import sys
import argparse
import itertools

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


def run(L, N, dx, adv_grad, extend, band_kind, nstep=80):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(NPF[1], float)
    n_h = n_h / np.linalg.norm(n_h)
    ax = int(np.argmax(np.abs(n_h)))
    rel = g.XYZ - np.array([L / 2] * 3)
    g.phi[1] = rel @ n_h
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / (MOB * DF)
    kw = dict(adv_grad=adv_grad, extend=extend)
    if band_kind == 'phys':
        kw['band_len'] = 1000e-9
        kw['iface_band'] = 2.0
    else:
        kw['band_cells'] = 20
    n0, c0 = g.iface_offset(k=1, l=0, axis=ax)
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, **kw)
        t += dt
    n1, c1 = g.iface_offset(k=1, l=0, axis=ax)
    if n0 == 0 or n1 == 0:
        return None
    v_axis = abs(c1 - c0) / t
    v_n = v_axis * abs(n_h[ax])          # ★ 几何因子：dz/dt = v_n/|n_axis|
    return v_n, v_n / (MOB * DF)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    Ns = [int(round(L / dx)) for dx in dxs]
    print('=' * 104)
    print('T11b —— Δx 依赖的来源隔离   L=%.0f nm  Δx=%s nm ⇒ N=%s' % (a.L_nm, a.dxs, Ns))
    print('  精确解：v_n = M·Δf = %.4e m/s（γ=0、Δf 常数 ⇒ 无曲率项）' % (MOB * DF))
    print('=' * 104)
    print('%-9s %-7s %-6s | %s' % ('adv_grad', 'extend', 'band',
                                   ' '.join('Δx=%-6.1f' % (d * 1e9) for d in dxs) +
                                   '   散布'))
    rows = []
    for adv, ext, bk in itertools.product(('central', 'upwind'),
                                          ('edt', None),
                                          ('phys', 'cells')):
        vals = []
        for N, dx in zip(Ns, dxs):
            r = run(L, N, dx, adv, ext, bk)
            vals.append(np.nan if r is None else r[1])
        vals = np.array(vals, float)
        sp = float((np.nanmax(vals) - np.nanmin(vals)) / abs(np.nanmean(vals)))
        rows.append((adv, ext, bk, vals, sp))
        print('%-9s %-7s %-6s | %s   %.4f'
              % (adv, str(ext), bk, ' '.join('%8.4f' % v for v in vals), sp), flush=True)
    print()
    # 归因：每个因素"改与不改"的散布差
    def sp_of(adv, ext, bk):
        for r in rows:
            if r[0] == adv and r[1] == ext and r[2] == bk:
                return r[4]
        return np.nan
    base = sp_of('central', 'edt', 'cells')
    print('  基准（central + edt + 20 胞）散布 = %.4f' % base)
    print('  逐项单独改动的效果：')
    for lab, key in (
            ("adv_grad central→upwind", ('upwind', 'edt', 'cells')),
            ("extend  edt→None", ('central', None, 'cells')),
            ("band    20 胞→物理 1000 nm", ('central', 'edt', 'phys'))):
        s = sp_of(*key)
        print('    %-30s 散布 %.4f（%+.4f）' % (lab, s, s - base))
    best = min(rows, key=lambda r: r[4])
    print()
    print('  ⇒ 散布最小的组合：adv_grad=%s, extend=%s, band=%s ⇒ 散布 %.4f'
          % (best[0], best[1], best[2], best[4]))
    print('  ⇒ 主导因素 = 使散布**下降最多**的那一项（见上表）')
    print('=' * 104)
    return 0


if __name__ == '__main__':
    sys.exit(main())
