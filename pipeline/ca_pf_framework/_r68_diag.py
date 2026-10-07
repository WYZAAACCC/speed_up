#!/usr/bin/env python3
"""R68: 诊断 `facet_project_one` 在解析长方体上的正对照失败（幂等性）。"""
import os
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
from _r68_facet_op import facet_project_one  # noqa: E402

N, L = 64, 4.0e-6
dx = L / N
a = np.array([1.0, 0.0, 0.0])
w = np.array([0.0, 1.0, 0.0])
nh = np.array([0.0, 0.0, 1.0])
ii = (np.arange(N) + 0.5) * dx
X, Y, Z = np.meshgrid(ii, ii, ii, indexing='ij')
d = np.stack([X - L / 2, Y - L / 2, Z - L / 2], -1)
Lb, Wb, Tb = 1600e-9, 700e-9, 635e-9
phi = np.maximum.reduce([np.abs(d @ a) - Lb / 2, np.abs(d @ w) - Wb / 2,
                         np.abs(d @ nh) - Tb / 2])
m = np.abs(phi) <= 0.5 * dx
pts = np.stack([X, Y, Z], -1)[m]
print('Δx = %.3f nm；界面带点数 %d' % (dx * 1e9, len(pts)))
for nm, u, exp in (('a', a, Lb / 2), ('w', w, Wb / 2), ('n', nh, Tb / 2)):
    pr = pts @ u
    half = (pr.max() - pr.min()) / 2
    print('  %-3s 期望半宽 %7.1f nm  实测 %7.1f nm  (min %8.1f max %8.1f)  偏差 %+.1f nm'
          % (nm, exp * 1e9, half * 1e9, pr.min() * 1e9, pr.max() * 1e9,
             (half - exp) * 1e9))
print('  φ<0 体素 = %d（解析应有 %d）'
      % (int((phi < 0).sum()),
         np.prod([int(Lb / dx), int(Wb / dx), int(Tb / dx)])))
phin, info = facet_project_one(phi, dx, (nh, a, w))
print('  info: v0=%d vp=%d s=%.4f v1=%d'
      % (info['v0'], info['vp'], info['s'], info['v1']))
