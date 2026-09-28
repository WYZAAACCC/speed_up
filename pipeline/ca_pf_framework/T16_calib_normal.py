#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T16_calib_normal.py --- **局部法向估计量的正对照**（R3 的修补）。

问题（T16 前置实测）
------------------
倾斜板条的宽面上，`np.gradient(φ_k)` 的**逐点法向在阶梯上振荡**
⇒ "宽面占比（夹角 <15°）"实测只有 **0.26–0.45**，而几何解析值 `a/(a+t)` 是 **0.82–0.90**。
⇒ 用这个量比 `a/(a+t)` 是**量具坏**，不是物理坏。

正对照构造
----------
`seed_plate` 造**长宽比已知**的板条（`2a × 2a × t`）⇒ 宽面面积占比解析值 = `a/(a+t)`。
比较四种法向口径：
  (i)  raw      —— `np.gradient(φ_k)`（当前用法）
  (ii) h=2dx    —— 中心差分**跨 2 胞**（`(φ[i+2]−φ[i−2])/(4dx)`）
  (iii) h=3dx   —— 跨 3 胞
  (iv) smooth   —— 先对 φ 做 3³ 盒滤波再求梯度

用法：python3 T16_calib_normal.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402
from scipy import ndimage                                       # noqa: E402

EPS0, _F, _M = variants()
C = C_cubic(134.0e9, 110.0e9, 36.0e9)
_rng = np.random.default_rng(0)
_best, N1 = None, None
for n in _rng.normal(size=(400, 3)):
    n = n / np.linalg.norm(n)
    val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[0], _lam_full(C, n), EPS0[0]))
    if _best is None or val < _best:
        _best, N1 = val, n


def grad_h(p, dx, h):
    """跨 h 胞的中心差分（周期）。"""
    g = []
    for ax in range(3):
        gp = np.roll(p, -h, axis=ax)
        gm = np.roll(p, h, axis=ax)
        g.append((gp - gm) / (2.0 * h * dx))
    return g


def frac_broad(g, k, n_ref, mode, dx, thr=15.0):
    reg = g.region()
    mk = (reg == k)
    if mk.sum() < 10:
        return np.nan, np.nan, 0
    nb = np.zeros(mk.shape, bool)
    for ax in range(3):
        nb |= (np.roll(reg, 1, axis=ax) == 0)
    iface = mk & nb
    p = g.phi[k]
    if mode == 'raw':
        gg = np.gradient(p, dx, edge_order=2)
    elif mode == 'smooth':
        gg = np.gradient(ndimage.uniform_filter(p, 3, mode='wrap'), dx, edge_order=2)
    else:
        gg = grad_h(p, dx, int(mode))
    gn = np.sqrt(sum(t ** 2 for t in gg)) + 1e-30
    nrm = np.stack([t / gn for t in gg], -1)[iface]
    nd = np.asarray(n_ref, float)
    nd = nd / np.linalg.norm(nd)
    ang = np.degrees(np.arccos(np.clip(np.abs(nrm @ nd), 0, 1)))
    return float((ang < thr).mean()), float(np.percentile(ang, 25)), ang.size


L = 2.4e-6
dx = 25e-9
N = int(round(L / dx))
print('=' * 100)
print('局部法向估计量正对照   L=%.1f µm Δx=%.0f nm' % (L * 1e6, dx * 1e9))
print('  解析：板条 2a×2a×t 的宽面面积占比 = a/(a+t)')
print('=' * 100)
print('%-22s %-10s | %s' % ('构型', '解析 a/(a+t)',
                            '  '.join('%-16s' % m for m in ('raw', 'h=2dx', 'h=3dx', 'smooth'))))
for a_nm, t_nm in ((240, 100), (240, 200), (240, 400), (120, 100)):
    g = W.LevelSetMulti(N, L, C=None, eps0=None, nv=1, gamma=0.15, Mob=1e-9,
                        df=[0.0, 2e8], workers=1, reinit_every=0)
    g.seed_plate(1, [L / 2] * 3, N1, a_nm * 1e-9, t_nm * 1e-9)
    g.init_parent()
    a, t = a_nm * 1e-9, t_nm * 1e-9
    pred = a / (a + t)
    cells = []
    p25s = []
    for mode in ('raw', '2', '3', 'smooth'):
        fb, p25, n = frac_broad(g, 1, N1, mode, dx)
        cells.append('%5.3f (p25 %4.1f)' % (fb, p25))
        p25s.append(p25)
    print('%-22s %-10.3f | %s' % ('2a=%d t=%d (2a/t=%.1f)' % (2 * a_nm, t_nm, 2 * a_nm / t_nm),
                                  pred, '  '.join('%-16s' % c for c in cells)))
    del g
print()
print('判读：哪个口径的"宽面占比"最接近解析 `a/(a+t)`，就是可用的那个。')
print('      同时看 `p25`：可靠口径下 p25 应很小（宽面法向准）。')
print('=' * 100)
