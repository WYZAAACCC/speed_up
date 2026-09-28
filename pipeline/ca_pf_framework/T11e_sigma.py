#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T11e_sigma.py --- T11 后续 (a1) 判决实验：`coef` 的配对符号该取**本胞**还是**种子胞**。

假设（T11d 推出）
-----------------
`coef = sigma_本胞 × vcanon_种子胞`。而 `vcanon` 已经含**种子胞**的 `sigma`
⇒ 两者相乘 = `(sigma_本胞/sigma_种子)·v_cell`。**跨过界面时 karr/larr 的次序翻转**
（一侧 winner 是 1、另一侧是 0）⇒ 这个比值**变号**：

  * **轴对齐前沿**：非界面胞的"最近界面胞"**总在同一侧** ⇒ 次序一致 ⇒ 比值 = +1 ⇒ 正确
  * **倾斜前沿**：阶梯的最近面片常在对角方向、**跨到另一侧** ⇒ 比值 = −1 ⇒ 前沿被拖慢

判决：把 `sigma` 换成**种子胞的**（`pair_sig_from_seed=True`，代码里已加开关、默认关闭）。

判据（两条同时成立才算修好）
--------------------------
  T11e-1 **倾斜档** `v_n/(MΔf)` → **1.000**（三档 Δx 散布 < 5%）
  T11e-2 **回归守卫**：轴对齐档**必须仍然 ≤1%**（修法不得牺牲已验证的正确性）

用法：python3 T11e_sigma.py [--L-nm 3000] [--dxs 40,50,62.5,100]
退出码：0 = 修好
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


def run(L, N, dx, n_h, from_seed, nstep=80, band=20):
    g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, gamma=0.0, Mob=MOB,
                        df=[0.0] + [DF] * NV, workers=1, reinit_every=0)
    g.pf = None
    g.pair_sig_from_seed = bool(from_seed)
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
        g.advance(dt, band_cells=band)
        t += dt
    n1, c1 = g.iface_offset(k=1, l=0, axis=ax)
    if n0 == 0 or n1 == 0:
        return None
    return (abs(c1 - c0) / t) * abs(n_h[ax]) / EXACT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--L-nm', type=float, default=3000.0)
    ap.add_argument('--dxs', type=str, default='40,50,62.5,100')
    a = ap.parse_args()
    L = a.L_nm * 1e-9
    dxs = [float(x) * 1e-9 for x in a.dxs.split(',')]
    Ns = [int(round(L / dx)) for dx in dxs]
    tilt = np.asarray(NPF[1], float)
    tilt = tilt / np.linalg.norm(tilt)
    print('=' * 104)
    print('T11e —— `coef` 配对符号：本胞 vs 种子胞   L=%.0f nm  Δx=%s nm ⇒ N=%s'
          % (a.L_nm, a.dxs, Ns))
    print('  下表 = v_n/(M·Δf)，精确值 1.000')
    print('=' * 104)
    print('%-34s | %s | %s' % ('算例', ' '.join('Δx=%-6.1f' % (d * 1e9) for d in dxs),
                               '散布'))
    res = {}
    for lab, n_h in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', tilt)):
        for fs, tag in ((False, '本胞 sigma（现状）'), (True, '种子胞 sigma（候选）')):
            vals = []
            for N, dx in zip(Ns, dxs):
                r = run(L, N, dx, n_h, fs)
                vals.append(np.nan if r is None else r)
            v = np.array(vals, float)
            res[(lab, fs)] = v
            sp = float((np.nanmax(v) - np.nanmin(v)) / abs(np.nanmean(v))) \
                if np.isfinite(v).any() else np.nan
            print('%-34s | %s | %.4f'
                  % ('%s / %s' % (lab, tag), ' '.join('%8.4f' % x for x in v), sp),
                  flush=True)
    print()
    t0, t1 = res[('倾斜 npref[1]', False)], res[('倾斜 npref[1]', True)]
    a0, a1 = res[('轴对齐 ẑ', False)], res[('轴对齐 ẑ', True)]

    def sp(v):
        return float((np.nanmax(v) - np.nanmin(v)) / abs(np.nanmean(v)))
    print('  T11e-1 倾斜档改后：散布 %.4f（判据 <0.05）；均值 %.4f（目标 1.000）'
          % (sp(t1), float(np.nanmean(t1))))
    print('  T11e-2 回归守卫（轴对齐）：散布 %.4f；最大偏差 %.2f%%'
          % (sp(a1), 100 * float(np.nanmax(np.abs(a1 - 1.0)))))
    ok1 = (sp(t1) < 0.05) and (abs(float(np.nanmean(t1)) - 1.0) < 0.05)
    ok2 = float(np.nanmax(np.abs(a1 - 1.0))) < 0.05
    print('  ⇒ 候选%s' % ('**成立**（倾斜修好且轴对齐不退化）' if (ok1 and ok2)
                          else '**不成立**（%s）'
                          % ('；'.join([x for x, o in
                                        (('倾斜未修好', ok1), ('轴对齐退化', ok2))
                                        if not o]))))
    print('=' * 104)
    return 0 if (ok1 and ok2) else 1


if __name__ == '__main__':
    sys.exit(main())
