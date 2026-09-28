#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_seedAR.py --- 核实 **"晶核态 AR"**：`seed_plate` 实际造出来的形状是不是
"半轴 `(R, R, t/2)` 的椭球"，以及**2D 截面口径**给出的 AR 与**几何 AR** 的关系。

动机（Round 32）：`_t21f.log` 的**种子态**读数 `AR=1.176`，而按 `(R=192 nm, t=200 nm)`
的椭球算，几何 AR 应是 `2R/t = 1.92`。**两者不符** ⇒ 若基准错，B3 的全部对比都要重算。

三把量具同时量同一个种子（R1：工具必须先自证）
------------------------------------------------
  **M1 三向尺度**：PCA 主轴上的投影 **`max−min`**（T15 已过正对照；`T20` 的种子正对照
       给出 477.8/476.2/100.1 vs 解析 480/480/100 ⇒ **偏差 ≤0.8%**）。
  **M2 2D 截面 AR**：过质心、法向沿主轴切三刀，各量 `longest/perpendicular`（Ter Haar 口径）。
  **M3 解析对照**：椭球 `(R, R, t/2)` 的三向尺度 = `(2R, 2R, t)`；
        垂直长轴的截面 = 椭圆 `(R, t/2)` ⇒ AR = `2R/t`。

用法：python3 _chk_seedAR.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402
from T21_beta_calib import section_ar_2d, _slice2d               # noqa: E402

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

N, dxn = 128, 25.0
dx = dxn * 1e-9
L = N * dx
R_SEED, T_SEED = 0.08 * L, 200e-9      # 与 T21 同规格：R=0.08L、t=200 nm

g = W.LevelSetMulti(N, L, C=C, eps0=EPS0, nv=NV, gamma=0.15, Mob=1e-9,
                    df=[0.0] + [2.0e8] * NV, workers=1, reinit_every=0)
g.seed_plate(1, [L / 2] * 3, np.asarray(NPF[1], float), R_SEED, T_SEED)
g.init_parent()
m = (g.region() == 1)
print('=' * 96)
print('_chk_seedAR —— 核实"晶核态"的 AR   规格 R=%.1f nm  t=%.1f nm  Δx=%.1f nm  N=%d'
      % (R_SEED * 1e9, T_SEED * 1e9, dxn, N))
print('  解析对照（椭球 (R,R,t/2)）：三向 = (2R, 2R, t) = (%.1f, %.1f, %.1f) nm'
      % (2 * R_SEED * 1e9, 2 * R_SEED * 1e9, T_SEED * 1e9))
print('  解析 2D：垂直长轴切 ⇒ 椭圆 (R, t/2) ⇒ **AR = 2R/t = %.3f**' % (2 * R_SEED / T_SEED))
print('-' * 96)
print('  M1 三向尺度（PCA 主轴上的 `max−min`，T15 已验证口径）：')
idx = np.argwhere(m)
p = (idx.astype(float) + 0.5) * dx
ctr = p.mean(0)
q = p - ctr
ev, evec = np.linalg.eigh(np.cov(q.T))
ext = []
for i in range(3):
    s = q @ evec[:, i]
    ext.append(float(s.max() - s.min()))
o = np.argsort(ext)[::-1]
print('     长=%.1f nm  中=%.1f nm  薄=%.1f nm  ⇒ 长/薄 = **%.3f**、中/薄 = %.3f'
      % (ext[o[0]] * 1e9, ext[o[1]] * 1e9, ext[o[2]] * 1e9,
         ext[o[0]] / ext[o[2]], ext[o[1]] / ext[o[2]]))
print('     （解析应为 2R/t = %.3f）⇒ 偏差 %+.1f%%'
      % (2 * R_SEED / T_SEED, 100 * (ext[o[0]] / ext[o[2]] / (2 * R_SEED / T_SEED) - 1)))
print('-' * 96)
print('  M2 2D 截面 AR（过质心、法向沿三个主轴）：')
ars = []
for i in range(3):
    ax = int(np.argmax(np.abs(evec[:, i])))
    c = int(round(ctr[ax] / dx - 0.5))
    c = max(0, min(N - 1, c))
    rem = [k for k in range(3) if k != ax]
    ar, Lg, Wd, A = section_ar_2d(_slice2d(m, ax, c, rem), dx)
    ars.append(ar)
    print('     法向=%s 层 %-3d ⇒ AR=%.3f（long=%.1f nm, perp=%.1f nm, 面积=%.3e m²）'
          % ('xyz'[ax], c, ar, Lg * 1e9, Wd * 1e9, A))
print('     三个截面的 AR 中位 = **%.3f**' % float(np.median(ars)))
print('-' * 96)
print('  ⇒ 结论：')
m2d = float(np.median(ars))
print('     · M1（三向尺度）给 长/薄 = %.3f，解析 %.3f ⇒ %s'
      % (ext[o[0]] / ext[o[2]], 2 * R_SEED / T_SEED,
         '一致 ✓' if abs(ext[o[0]] / ext[o[2]] / (2 * R_SEED / T_SEED) - 1) < 0.15
         else '**不一致 ✗**'))
print('     · M2（2D 截面）给 %.3f —— 与 M1 **不同**（%.3f vs %.3f）'
      % (m2d, m2d, ext[o[0]] / ext[o[2]]))
print('     ⇒ 若 M1 与解析一致而 M2 不一致，则**"晶核几何 AR"应以 M1 为准**，')
print('       而 T21 用的 M2 口径**系统性低于**几何 AR —— 这会改变 B3 的"种子基准"。')
print('=' * 96)
