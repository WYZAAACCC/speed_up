import io
src = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import numpy as np
import ca3d
from ca3d import CA3D, IRF

def support(P, n):
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))

theta = math.radians(35.0)
n = np.array([math.sin(theta), 0.0, math.cos(theta)])
irf = IRF(); V = float(irf(16.0)); dx = 4e-6
dt = dx / (4.0 * V)
rng = np.random.default_rng(100)
quats = [ca3d.rand_quat(rng) for _ in range(9)]
for mode in ("decentered", "analytic"):
    devs = []
    for trial, q in enumerate(quats):
        ca = CA3D(60, 60, 60, dx, irf=irf, seed=1000 + trial, capture=mode)
        g = ca.add_grain(30, 30, 30, q)
        for _ in range(60):
            ca.step(dt, ca.T_iso(16.0), window="full")
        X, Y, Z = ca.coords()
        sp = X * n[0] + Y * n[1] + Z * n[2]
        s0 = float(sp[30, 30, 30])
        m = ca.gid == g
        L_end = V * 60 * dt
        s = support(ca.axes[g], n)
        devs.append((float(sp[m].max()) - s0 - L_end / s) / dx)
    a = np.array(devs)
    print("{:11s} dev/dx: mean {:+.3f}  std {:.3f}  max|dev| {:.3f}".format(mode, a.mean(), a.std(), abs(a).max()))
'''
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/_diag_analytic.py", "w", encoding="utf-8").write(src)
print("written")