import io
src = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自由律偏差 vs 生长长度（判断能否靠拉长生长提高选择测试的信噪比）"""
import math
import numpy as np
import ca3d
from ca3d import CA3D, IRF

def support(P, n):
    n = np.array(n, float); n /= np.linalg.norm(n)
    return sum(abs(float(P[:, a] @ n)) for a in range(3))

theta = math.radians(35.0)
n = np.array([math.sin(theta), 0.0, math.cos(theta)])
irf = IRF(); dTu = 16.0; V = float(irf(dTu))
dx = 4e-6
dt = dx / (4.0 * V)
rng = np.random.default_rng(100)
quats = [ca3d.rand_quat(rng) for _ in range(9)]
for nst in (60, 240, 480):
    L_end = V * nst * dt
    N = int(L_end / dx * 2.2) + 40
    devs = []
    for trial, q in enumerate(quats):
        ca = CA3D(N, N, N, dx, irf=irf, seed=2000 + trial)
        c0 = N // 2
        g = ca.add_grain(c0, c0, c0, q)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        X, Y, Z = ca.coords()
        sp = X * n[0] + Y * n[1] + Z * n[2]
        s0 = float(sp[c0, c0, c0])
        m = ca.gid == g
        adv = float(sp[m].max()) - s0
        s = support(ca.axes[g], n)
        devs.append((adv - L_end / s) / dx)
    a = np.array(devs)
    print("Vt={:>5.0f} dx  N={:>4}  dev mean {:+.2f}  std {:.2f}  max|dev| {:.2f} cells | s-span of pred = {:.1f} cells".format(
        L_end / dx, N, a.mean(), a.std(), abs(a).max(),
        L_end / min(support(ca.axes[g], n) for g in range(1, 10)) - L_end / max(support(ca.axes[g], n) for g in range(1, 10))))
'''
io.open("/mnt/f/speed_up/pipeline/ca_pf_framework/_t6diag2.py", "w", encoding="utf-8").write(src)
print("written")