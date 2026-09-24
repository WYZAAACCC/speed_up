#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_dbg_oct1.py --- 打印一个失败算例的全部中间量（scalar vs 我的）'''
import sys, math
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, quat_to_axes, rand_quat
rng = np.random.default_rng(0)
qs = [rand_quat(rng) for _ in range(2)]
csrc = np.array([rng.uniform(1, 7) for _ in range(3)])
x0 = np.array([1.0, 0.0, 1.0])
xnbr = csrc + x0
P = quat_to_axes(qs[1])            # 与单元测试的 trial=1 对齐
d = xnbr - csrc
crit = float(sum(abs(P[:, k] @ d) for k in range(3)))
print('csrc =', np.round(csrc, 6), ' xnbr =', np.round(xnbr, 6), ' crit =', round(crit, 6))
print('P ='); print(np.round(P, 6))
pos = [(P[:, k] @ x0) > 0.0 for k in range(3)]
print('pos =', pos, ' (p_k·x0 =', [round(float(P[:, k] @ x0), 6) for k in range(3)], ')')
diag = [P[:, k] * (2.0 * (1 if pos[k] else 0) - 1.0) for k in range(3)]
T = [csrc + crit * diag[k] for k in range(3)]
dd = [np.linalg.norm(T[k] - xnbr) for k in range(3)]
print('dist_to_corner =', [round(x, 6) for x in dd])
c01 = dd[0] < dd[1]; c12 = dd[1] < dd[2]; c20 = dd[2] < dd[0]
ti = 2 * (int(c20) - int(c12)) * int(c20) + (int(c12) - int(c01)) * int(c12)
print('booleans c01,c12,c20 =', c01, c12, c20, '=> ti =', ti, ' argmin =', int(np.argmin(dd)))
xc = T[ti]; x1 = T[(ti+1) % 3]; x2 = T[(ti+2) % 3]
d1 = np.linalg.norm(xc - x1); d2 = np.linalg.norm(xc - x2)
j1 = float((xnbr - x1) @ (xc - x1)) / d1; j1n = d1 - j1
j2 = float((xnbr - x2) @ (xc - x2)) / d2; j2n = d2 - j2
s3 = math.sqrt(3.0)
l12 = 0.5 * (min(j1, s3) + min(j1n, s3)); l13 = 0.5 * (min(j2, s3) + min(j2n, s3))
print('j1,j1n =', round(j1,6), round(j1n,6), ' j2,j2n =', round(j2,6), round(j2n,6))
print('l12,l13 =', round(l12,6), round(l13,6), ' => lnew =', round(math.sqrt(2)*max(l12,l13), 6))
print()
print('注意: ExaCA 的 tri 角点是【八面体三个顶点】= csrc ± crit·p_k。')
print('      若 crit 用"当前胞的中心到邻居的 L1"，(xc-x1) 的长度应 = sqrt(2)*crit =', round(math.sqrt(2)*crit,6))
print('      实测 d1 =', round(d1,6), ' d2 =', round(d2,6))