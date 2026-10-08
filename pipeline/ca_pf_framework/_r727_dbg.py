#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_dbg.py —— 探针：打印 `grad_sep` / `lsq_plane_ref` 的梯度幅度与形状。"""
import numpy as np
import sys
sys.path.insert(0, '.')
from _r727_lsq_exact import grad_sep, lsq_plane_ref, conv1, sep_moments

N = 24
dx = 0.0625e-6
c = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
ctr = np.array([X.mean(), Y.mean(), Z.mean()])
R = 0.30 * N * dx
rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
f = rr - R

S, Mx, My, Mz = sep_moments(f, dx)
for nm, a in (('S', S), ('Mx', Mx), ('My', My), ('Mz', Mz)):
    print('%-4s shape=%s  min=%.4e max=%.4e' % (nm, a.shape, a.min(), a.max()))

g1 = grad_sep(f, dx)
g2 = lsq_plane_ref(f, dx)
n1 = np.sqrt(sum(g ** 2 for g in g1))
n2 = np.sqrt(sum(g ** 2 for g in g2))
print()
print('n1 (可分)   min=%.4e max=%.4e median=%.4e' % (n1.min(), n1.max(), np.median(n1)))
print('n2 (参考)   min=%.4e max=%.4e median=%.4e' % (n2.min(), n2.max(), np.median(n2)))
print('n1*dx       median=%.6f  (应 ≈1)' % (np.median(n1) * dx))
print('n2*dx       median=%.6f  (应 ≈1)' % (np.median(n2) * dx))
mask = (n1 > 1e-6) & (n2 > 1e-6)
print('mask.sum() = %d / %d' % (mask.sum(), n1.size))
# 逐点夹角
u1 = np.stack([g / (n1 + 1e-300) for g in g1], -1)
u2 = np.stack([g / (n2 + 1e-300) for g in g2], -1)
ca = np.clip(np.abs(np.einsum('...i,...i->...', u1, u2)), 0, 1)
ang = np.degrees(np.arccos(ca))
print('全盒夹角 max=%.4f°  median=%.4f°' % (ang.max(), np.median(ang)))
print('mask 内夹角 max=%.4e°  median=%.4e°'
      % (ang[mask].max(), np.median(ang[mask])))
# 梯度分量相对差
d = np.stack(g1, -1) - np.stack(g2, -1)
print()
print('梯度分量绝对差 max=%.4e ; 参考梯度 max=%.4e ; 相对=%.4e'
      % (np.abs(d).max(), np.abs(np.stack(g2, -1)).max(),
         np.abs(d).max() / (np.abs(np.stack(g2, -1)).max() + 1e-300)))
