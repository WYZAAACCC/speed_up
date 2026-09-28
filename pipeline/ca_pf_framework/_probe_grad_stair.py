#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_probe_grad_stair.py —— 决定性一步：量**离散 |∇φ|** 在倾斜阶梯上被低估多少。

为什么这一步能定位
------------------
T11c 的算例里 `γ=0`、`pf=None` ⇒ `dG_cell = df_k − df_l` 在**空间上是常数**
⇒ 速度延拓 / 带宽 / 最近胞逻辑**全都无关**；方程退化为
    `φ_t + c·|∇φ| = 0`     （c = M·Δf 常数）
其精确解是**纯平移**，前提是 `|∇φ| ≡ 1`。所以倾斜档的赤字**只能**来自
"离散 `|∇φ|` 在阶梯上不等于 1"。

本探针直接构造 SDF `φ = (x−c)·n`，量界面带内 `|∇φ|` 的**中位数与均值**：
  * 轴对齐 n=ẑ  ⇒ 应恰为 1
  * 倾斜 n=npref[1] ⇒ 若 < 1，则预测速度比 = 该值（与 T11c 实测对照）
同时给出**两种梯度格式**（central / Godunov 迎风）与**差分场**`d=φ_k−φ_l` 的情形。
"""
import os
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
_rng = np.random.default_rng(0)
_best, TILT = None, None
for n in _rng.normal(size=(400, 3)):
    n = n / np.linalg.norm(n)
    val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[0], _lam_full(C, n), EPS0[0]))
    if _best is None or val < _best:
        _best, TILT = val, n

L = 3000e-9
print('%-8s %-26s %-12s %-12s %-12s' %
      ('Δx(nm)', '法向 / 格式', 'median|∇φ|', 'mean|∇φ|', '带内胞数'))
for dx_nm in (40.0, 50.0, 62.5, 100.0, 25.0):
    dx = dx_nm * 1e-9
    N = int(round(L / dx))
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                        df=[0.0, 1e8], workers=1, reinit_every=0, nv=1)
    rel = g.XYZ - np.array([L / 2] * 3)
    for lab, n in (('轴对齐 ẑ', np.array([0.0, 0, 1.0])), ('倾斜 npref[1]', TILT)):
        d = rel @ n
        g.phi[1] = d
        g.phi[0] = -d
        for tag, f in (('central', lambda p: np.sqrt(sum(
                t ** 2 for t in np.gradient(p, dx, edge_order=2)))),
                ('upwind(Godunov)', lambda p: W.upwind_grad(
                    p, np.sign(p), dx))):
            gm = f(g.phi[1])
            band = np.abs(g.phi[1]) <= 2.0 * dx
            print('%-8.1f %-26s %-12.4f %-12.4f %-12d'
                  % (dx_nm, '%s / %s' % (lab, tag), float(np.median(gm[band])),
                     float(np.mean(gm[band])), int(band.sum())))
    # 差分场 d = φ_1 − φ_0 = 2φ_1（|∇d| 应为 2）
    dd = g.phi[1] - g.phi[0]
    gm = np.sqrt(sum(t ** 2 for t in np.gradient(dd, dx, edge_order=2)))
    band = np.abs(dd) <= 4.0 * dx
    print('%-8.1f %-26s %-12.4f %-12.4f %-12d'
          % (dx_nm, '差分场 d=φ1−φ0 / central', float(np.median(gm[band])),
             float(np.mean(gm[band])), int(band.sum())))
    del g
    print()
print('预测：若 `φ_t + c|∇φ| = 0` 且 `|∇φ|` 的中位数为 m，则观测速度比 ≈ m')
print('（与 T11c 实测 0.674/0.616/0.597/0.520 对照）')
