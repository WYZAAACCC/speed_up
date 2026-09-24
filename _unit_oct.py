#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_unit_oct.py --- oct_recenter 单元测试：与 ExaCA createNewOctahedron 的逐行标量版对比'''
import sys, math
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, quat_to_axes
from ca3d import rand_quat


def exaca_scalar(csrc, xnbr, crit, P, s3=math.sqrt(3.0)):
    """ExaCA src/CAinterface.hpp::createNewOctahedron 的原样转写（P 的列 = p1,p2,p3）"""
    x0 = xnbr - csrc
    pos = [(P[:, k] @ x0) > 0.0 for k in range(3)]           # ★ 注意: 严格 >
    diag = [P[:, k] * (2.0 * (1 if pos[k] else 0) - 1.0) for k in range(3)]
    T = [csrc + crit * diag[k] for k in range(3)]
    d = [np.linalg.norm(T[k] - xnbr) for k in range(3)]
    c01 = d[0] < d[1]; c12 = d[1] < d[2]; c20 = d[2] < d[0]
    ti = 2 * (int(c20) - int(c12)) * int(c20) + (int(c12) - int(c01)) * int(c12)
    mind = d[ti]; xc = T[ti]
    x1 = T[(ti + 1) % 3]; x2 = T[(ti + 2) % 3]
    d1 = np.linalg.norm(xc - x1); d2 = np.linalg.norm(xc - x2)
    j1, j1n, j2, j2n = 0.0, d1, 0.0, d2
    if mind != 0.0:
        j1 = float((xnbr - x1) @ (xc - x1)) / d1; j1n = d1 - j1
        j2 = float((xnbr - x2) @ (xc - x2)) / d2; j2n = d2 - j2
    l12 = 0.5 * (min(j1, s3) + min(j1n, s3))
    l13 = 0.5 * (min(j2, s3) + min(j2n, s3))
    lnew = math.sqrt(2.0) * max(l12, l13)
    cap = xc - csrc
    uhat = cap / max(np.linalg.norm(cap), 1e-30)
    cnew = xc - lnew * uhat
    return lnew, cnew


ca = CA3D(8, 8, 8, 1e-6)
rng = np.random.default_rng(0)
print('%-6s %-28s %-28s %s' % ('算例', 'scalar (ExaCA 原样)', '我的矢量化', '一致?'))
bad = 0
for trial in range(8):
    q = rand_quat(rng)
    P = quat_to_axes(q)
    csrc = np.array([rng.uniform(1, 7) for _ in range(3)])
    x0 = np.array([rng.choice([-1., 0., 1.]) for _ in range(3)])
    if not x0.any():
        x0 = np.array([1., 0., 0.])
    xnbr = csrc + x0
    d = xnbr - csrc
    crit = float(sum(abs(P[:, k] @ d) for k in range(3)))
    ls, cs = exaca_scalar(csrc, xnbr, crit, P)
    # 我的实现
    g = ca.add_grain(2, 2, 2, quat=q)
    ca.axes[g] = P
    # 直接调矢量化接口（批量=1）
    import types
    Pg = ca.axes[g]
    # 用 oct_recenter（需要 gvec / csrc(2D) / xnbr(2D) / crit(1D)）
    cs2 = csrc[None, :]; xn2 = xnbr[None, :]; cr2 = np.array([crit])
    # 临时把 axes[g] 指向 g=1
    lv, cv = ca.oct_recenter(np.array([g]), cs2, xn2, cr2)   # ← 用【本 trial 的】grain
    ok = abs(lv[0] - ls) < 1e-10 and np.allclose(cv[0], cs, atol=1e-10)
    if not ok:
        bad += 1
    print('%-6d l: %.10f vs %.10f | c 差 %.2e | %s' % (
        trial, ls, lv[0], np.linalg.norm(cv[0] - cs), 'OK' if ok else '**不一致**'))
print()
print('不一致数 =', bad, '/ 8')