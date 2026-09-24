#!/usr/bin/env python3
"""最小复现: phi[:, mask] /= s[mask] 真的会写回吗？"""
import numpy as np

phi = np.zeros((3, 2, 2, 2))
phi[:, 0, 0, 0] = [0.7, 0.5, 0.19]          # 和 = 1.39 > 1
s = phi.sum(0)
over = s > 1.0
print('s[0,0,0] =', s[0, 0, 0], 'over.any() =', over.any(), 'over.sum() =', over.sum())
phi[:, over] /= s[over]
print('写法 A (phi[:, over] /= s[over]) 之后 s[0,0,0] =', phi.sum(0)[0, 0, 0])

phi2 = np.zeros((3, 2, 2, 2))
phi2[:, 0, 0, 0] = [0.7, 0.5, 0.19]
s2 = phi2.sum(0)
ov2 = s2 > 1.0
phi2[:, ov2] = phi2[:, ov2] / s2[ov2]
print('写法 B (显式赋值)          之后 s[0,0,0] =', phi2.sum(0)[0, 0, 0])
