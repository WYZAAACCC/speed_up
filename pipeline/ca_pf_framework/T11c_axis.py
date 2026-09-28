#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11c_axis.py --- T11 后续 (a1)：判定"阶梯"是不是系统性速度误差的机制，并试 PDE 延拓。

决定性对照（**单变量**）
------------------------
同一套代码、同一 Δf、同一 Δx 序列，**只改界面法向**：
  · `n = ẑ`（**与网格轴对齐** ⇒ 无阶梯）
  · `n = npref[1]`（倾斜 ⇒ 有阶梯）
若"轴对齐 ⇒ `v/(MΔf) ≈ 1`"而"倾斜 ⇒ 明显偏离"，则**阶梯机制确证**。

再试一条候选修法：
  · `pair_kernel=True` 走的是 **PDE 延拓**（`extend_along_normal`）而不是 EDT 最近胞延拓
    （代码注释记载它当年平界面标定实测 0.00，未通过）—— 这里在**同一把尺子**下再量一次。

用法：python3 T11c_axis.py [--L-nm 3000] [--dxs 40,50,62.5]
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


def run(L, N, dx, n_h, pair_kernel=False, nstep=80, band=20):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    n_h = np.asarray(n_h, float)
    n_h = n_h / np.linalg.norm(n_h)
    ax = int(np.argmax(np.abs(n_h)))
    rel = g.XYZ - np.array([L / 2] * 3)
    d = rel @ n_h
    g.phi[1] = d
    for j in range(1, g.nreg):
        if j != 1:
            g.phi[j] = 1e3
    g.init_parent()
    dt = 0.15 * dx / EXACT
    n0, c0 = g.iface_offset(k=1, l=0, axis=ax)
    t = 0.0
    for _ in range(nstep):
        g.advance(dt, band_cells=band, pair_kernel=pair_kernel)
        t += dt
    n1, c1 = g.iface_offset(k=1, l=0, axis=ax)
    if n0 == 0 or n1 == 0:
        return None
    v_n = (abs(c1 - c0) / t) * abs(n_h[ax])
    return v_n / EXACT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5,100')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    Ns = [int(round(L / dx)) for dx in dxs]
    tilted = np.asarray(NPF[1], float)
    tilted = tilted / np.linalg.norm(tilted)
    cases = [('轴对齐 ẑ', np.array([0.0, 0, 1.0]), False),
             ('倾斜 npref[1]', tilted, False),
             ('倾斜 + PDE 延拓(pair_kernel)', tilted, True)]
    print('=' * 104)
    print('T11c —— 阶梯机制判定 + PDE 延拓对照   L=%.0f nm  Δx=%s nm ⇒ N=%s'
          % (a.L_nm, a.dxs, Ns))
    print('  精确解 v_n = M·Δf = %.4e m/s ; 下表 = v_n/(M·Δf)' % EXACT)
    print('=' * 104)
    print('%-30s | %s | %s' % ('算例', ' '.join('Δx=%-6.1f' % (d * 1e9) for d in dxs),
                               '散布'))
    res = {}
    for lab, n_h, pk in cases:
        vals = []
        for N, dx in zip(Ns, dxs):
            r = run(L, N, dx, n_h, pair_kernel=pk)
            vals.append(np.nan if r is None else r)
        vals = np.array(vals, float)
        res[lab] = vals
        sp = float((np.nanmax(vals) - np.nanmin(vals)) / abs(np.nanmean(vals))) \
            if np.isfinite(vals).any() else np.nan
        print('%-30s | %s | %.4f'
              % (lab, ' '.join('%8.4f' % v for v in vals), sp), flush=True)
    print()
    axv = res['轴对齐 ẑ']
    tiv = res['倾斜 npref[1]']
    print('  ① 轴对齐档是否精确？偏差 = %s'
          % ' '.join('%+.2f%%' % (100 * (v - 1)) for v in axv))
    print('  ② 轴对齐 vs 倾斜的差距 = %s'
          % ' '.join('%+.4f' % (t - a_) for t, a_ in zip(tiv, axv)))
    ok_axis = bool(np.nanmax(np.abs(axv - 1.0)) < 0.05)
    print('  ⇒ 阶梯机制：%s'
          % ('**确证**（轴对齐精确、倾斜偏差大）' if ok_axis else
             '**未确证**（轴对齐也不精确 ⇒ 还有别的机制）'))
    print()
    pkv = res['倾斜 + PDE 延拓(pair_kernel)']
    print('  ③ PDE 延拓 vs EDT（倾斜档）：%s'
          % ' '.join('%+.4f' % (p - t) for p, t in zip(pkv, tiv)))
    print('     散布：EDT %.4f ; PDE %.4f'
          % (float((np.nanmax(tiv) - np.nanmin(tiv)) / abs(np.nanmean(tiv))),
             float((np.nanmax(pkv) - np.nanmin(pkv)) / abs(np.nanmean(pkv)))
             if np.isfinite(pkv).any() else np.nan))
    print('=' * 104)
    return 0


if __name__ == '__main__':
    sys.exit(main())
