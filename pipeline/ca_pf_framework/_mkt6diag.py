import io
P = "/mnt/f/speed_up/pipeline/ca_pf_framework/_t6diag.py"
src = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单晶自由生长律的逐取向偏差（量出格点路径近似的地板）"""
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
for dx in (4e-6, 2e-6, 1e-6):
    dt = dx / (4.0 * V)
    nst = 60
    L_end = V * nst * dt
    rng = np.random.default_rng(100)
    devs = []
    for trial in range(9):
        q = ca3d.rand_quat(rng)
        ca = CA3D(40, 40, 40, dx, irf=irf, seed=1000 + trial)
        g = ca.add_grain(20, 20, 20, q)
        for _ in range(nst):
            ca.step(dt, ca.T_iso(dTu), window="full")
        X, Y, Z = ca.coords()
        sp = X * n[0] + Y * n[1] + Z * n[2]
        s0 = float(sp[20, 20, 20])
        m = ca.gid == g
        adv = float(sp[m].max()) - s0
        s = support(ca.axes[g], n)
        devs.append((adv - L_end / s) / dx)
        print("  dx={:.0f}um trial={} s={:.4f} adv={:.2f}dx pred={:.2f}dx dev={:+.2f}dx".format(
            dx * 1e6, trial, s, adv / dx, L_end / s / dx, (adv - L_end / s) / dx))
    a = np.array(devs)
    print("  ==> dx={:.0f} um: dev mean {:+.2f}  std {:.2f}  max|dev| {:.2f} cells (Vt={:.0f}dx)".format(
        dx * 1e6, a.mean(), a.std(), abs(a).max(), L_end / dx))
    print("")
'''
io.open(P, "w", encoding="utf-8").write(src)
print("written")