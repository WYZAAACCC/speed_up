#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_verify_cell_geom.py --- 三模式单晶包络几何对比（对解析 L1 球 r=ℓ/Σ）
判据：与解析律的偏离应 <=1.5 胞；decentered 预期严重偏离（25~40% 径向亏损）
'''
import sys, os, math
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, IRF, T_LIQ
N, DX, DTU = 81, 1.0e-6, 12.0
ELL_T = 15e-6
Q = None

def qaa(axis, deg):
    a = np.array(axis, float); a /= np.linalg.norm(a)
    th = math.radians(deg)
    return (math.cos(th/2), *(a*math.sin(th/2)))

def run(mode):
    ca = CA3D(N, N, N, DX, irf=IRF(), seed=7, capture=mode)
    c = (N//2, N//2, N//2)
    g = ca.add_grain(c[0], c[1], c[2], quat=qaa((0.3, 0.7, 0.2), 37.0))
    P = ca.axes[g]
    V = float(ca.irf.capped(np.array([DTU]))[0][0])
    dt = DX / (4.0 * V)
    nst = int(round(ELL_T / (V * dt)))
    t = 0.0
    for s in range(nst):
        ca.t = t
        ca.step(dt, ca.T_iso(DTU), window='full')
        t += dt
    ell = V * nst * dt
    solid = ca.gid > 0
    out = {}
    for nm, cv in (('<100>', (1,0,0)), ('<110>', (1,1,0)), ('<111>', (1,1,1)), ('mid', (1,0.45,0.15))):
        cv = np.array(cv, float); cv /= np.linalg.norm(cv)
        nw = P @ cv
        sig = sum(abs(float(P[:, a] @ nw)) for a in range(3))
        sm = 0.0
        for rr in np.arange(0, 2.5*ell, 0.1*DX):
            p = (np.array(c) + 0.5) * DX + rr * nw
            idx = np.floor(p / DX).astype(int)
            if np.any(idx < 0) or np.any(idx >= N):
                break
            if solid[idx[0], idx[1], idx[2]]:
                sm = rr
        out[nm] = (sm / ell, 1.0 / sig, sig)
    return out, ell / DX

print('单晶包络径向可达 r/ℓ（解析 = 1/Σ）；ℓ = %.1f 胞' % (ELL_T / DX))
print('%-12s %-24s %-24s %-24s' % ('模式', '<100> 实测(解析)', '<110> 实测(解析)', '<111> 实测(解析)'))
res = {}
for mode in ('cell', 'envelope', 'decentered'):
    o, ellc = run(mode)
    res[mode] = o
    print('%-12s %.3f (%.3f)          %.3f (%.3f)          %.3f (%.3f)' % (
        mode, o['<100>'][0], o['<100>'][1], o['<110>'][0], o['<110>'][1], o['<111>'][0], o['<111>'][1]))
print()
print('%-12s %-28s %-10s' % ('模式', '与解析律最大偏离(胞)', '判定'))
for mode in ('cell', 'envelope', 'decentered'):
    o = res[mode]
    dev = max(abs(o[k][0] - o[k][1]) * (ELL_T / DX) for k in ('<100>', '<110>', '<111>', 'mid'))
    print('%-12s %-28.2f %s' % (mode, dev, 'PASS' if dev <= 1.5 else 'FAIL'))