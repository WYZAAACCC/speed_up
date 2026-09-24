#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_mirror.py --- 按 ExaCA Inp_TwoGrainDirSolidification 的初始条件在我的 CA 里重做
比较对象: (a) 解析预测(WC 择优方向 + 会合面 locus) ; (b) 我的两种捕获模式
记账: dx 由 1µm 放大到 4µm（同物理尺寸 200µm，50^3）；用 ExaCA 自己的 In625 三次律 V(dT)
'''
import os, sys, math, time, json
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, T_LIQ

# ---- ExaCA 的 In625 界面响应（原样照抄它的材料文件） ----
A, B, C = -1.0302e-7, 1.0533e-4, 2.2196e-3
FREEZING = 210.0


class CubicIRF(object):
    def __init__(self):
        self.dT_lo = 0.0
        self.dT_hi = FREEZING
        self.V_at_hi = A * FREEZING ** 3 + B * FREEZING ** 2 + C * FREEZING

    def __call__(self, dT):
        dT = np.asarray(dT, float)
        return np.clip(A * dT ** 3 + B * dT ** 2 + C * dT, 0.0, self.V_at_hi)

    def capped(self, dT):
        dT = np.asarray(dT, float)
        n_low = int(np.count_nonzero(dT < 0.0))
        dTu = np.clip(dT, 0.0, FREEZING)
        return (np.clip(A * dTu ** 3 + B * dTu ** 2 + C * dTu, 0.0, self.V_at_hi),
                dTu, n_low, 0)


DX = 4.0e-6            # ExaCA 用 1µm；本机放大到 4µm（记账）
N = 50                 # 50^3 = 200 µm 立方（与 ExaCA 的 200µm 域同物理尺寸）
G = 5.0e5              # K/m
R = 0.3                # m/s
DT0 = 10.0             # K  初始过冷（ExaCA InitUndercooling）
P25 = np.load('/mnt/f/speed_up/bench/exaca/P25.npy')
P99 = np.load('/mnt/f/speed_up/bench/exaca/P99.npy')
# ExaCA 种子 (100,50) 与 (100,150) @200µm/1µm => 物理 (100µm, 50µm) 与 (100µm,150µm)
SEEDS = [('25', (25, 12)), ('9936', (25, 37))]


def quat_from_P(P):
    '''由晶体轴矩阵反解一个四元数（add_grain 接受 quat）'''
    tr = P[0, 0] + P[1, 1] + P[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w = 0.25 * s; x = (P[2, 1] - P[1, 2]) / s; y = (P[0, 2] - P[2, 0]) / s; z = (P[1, 0] - P[0, 1]) / s
    elif P[0, 0] > P[1, 1] and P[0, 0] > P[2, 2]:
        s = math.sqrt(1.0 + P[0, 0] - P[1, 1] - P[2, 2]) * 2
        w = (P[2, 1] - P[1, 2]) / s; x = 0.25 * s; y = (P[0, 1] + P[1, 0]) / s; z = (P[0, 2] + P[2, 0]) / s
    elif P[1, 1] > P[2, 2]:
        s = math.sqrt(1.0 + P[1, 1] - P[0, 0] - P[2, 2]) * 2
        w = (P[0, 2] - P[2, 0]) / s; x = (P[0, 1] + P[1, 0]) / s; y = 0.25 * s; z = (P[1, 2] + P[2, 1]) / s
    else:
        s = math.sqrt(1.0 + P[2, 2] - P[0, 0] - P[1, 1]) * 2
        w = (P[1, 0] - P[0, 1]) / s; x = (P[0, 2] + P[2, 0]) / s; y = (P[1, 2] + P[2, 1]) / s; z = 0.25 * s
    return (w, x, y, z)


def run(mode, nst=5000):
    irf = CubicIRF()
    ca = CA3D(N, N, N, DX, irf=irf, seed=1, capture=mode)
    g1 = ca.add_grain(SEEDS[0][1][0], SEEDS[0][1][1], 0, quat=quat_from_P(P25))
    g2 = ca.add_grain(SEEDS[1][1][0], SEEDS[1][1][1], 0, quat=quat_from_P(P99))
    Vmax = irf.V_at_hi
    dt = DX / (4.0 * Vmax)
    tt = 0.0
    for s in range(nst):
        ca.t = tt
        dT = DT0 + G * (R * tt - np.arange(N)[None, None, :] * DX)
        T = T_LIQ - np.clip(dT, -300.0, 300.0)
        T = np.broadcast_to(T, ca.shape).copy()
        ca.step(dt, T, window='full')
        tt += dt
        if (ca.gid == 0).sum() == 0:
            break
    return ca, g1, g2, s + 1, dt


print('ExaCA In625 界面响应: V(dT)=%.4e dT^3 + %.4e dT^2 + %.4e dT, 上限 V(210K)=%.3f m/s' % (
    A, B, C, A * FREEZING ** 3 + B * FREEZING ** 2 + C * FREEZING))
print('镜像算例: dx=%.1f µm, 域 %d^3 (=%.0f µm), G=%.1e K/m, R=%.2f m/s, ΔT0=%.0f K' % (
    DX * 1e6, N, N * DX * 1e6, G, R, DT0))
print()

out = {}
for mode in ('envelope', 'decentered'):
    t0 = time.time()
    ca, g1, g2, nst, dt = run(mode)
    wall = time.time() - t0
    gg = ca.gid
    n1 = int((gg == g1).sum()); n2 = int((gg == g2).sum())
    h1 = np.nonzero((gg == g1).sum(axis=(0, 1)))[0]
    h2 = np.nonzero((gg == g2).sum(axis=(0, 1)))[0]
    # 会合面: 每个 z 层里两晶粒的 y 分界
    yb = []
    for k in range(N):
        row = gg[:, :, k]
        ia = np.nonzero((row == g1).any(axis=0))[0]
        ib = np.nonzero((row == g2).any(axis=0))[0]
        if len(ia) and len(ib):
            yb.append((k, int(ia.max()), int(ib.min())))
    # 解析 locus: 每层里 sup_g1 = sup_g2 的 y
    pred = []
    for k in range(N):
        ys = np.arange(N)
        xs = np.full(N, 25)
        s1 = ca.envelope_sup(g1, xs, ys, np.full(N, k))
        s2 = ca.envelope_sup(g2, xs, ys, np.full(N, k))
        d = s1 - s2
        cross = np.nonzero(np.sign(d[:-1]) * np.sign(d[1:]) < 0)[0]
        if len(cross):
            i = cross[0]
            y0 = i + d[i] / (d[i] - d[i + 1])
            pred.append((k, y0))
    print('--- 模式 %s  (%d 步, %.0f s, dt=%.2e s)' % (mode, nst, wall, dt))
    print('    GrainID 25   : %6d 胞  高度 z=%d..%d' % (n1, h1[0] if len(h1) else -1, h1[-1] if len(h1) else -1))
    print('    GrainID 9936 : %6d 胞  高度 z=%d..%d' % (n2, h2[0] if len(h2) else -1, h2[-1] if len(h2) else -1))
    print('    => 体积更大/更高的是 %s ; 解析预测更快的是 GrainID 9936  => %s' % (
        'GrainID 9936' if n2 > n1 else 'GrainID 25', 'PASS' if n2 > n1 else 'FAIL'))
    if yb and pred:
        d = [abs(y[1] + 0.5 - p[1]) for y, p in zip(yb, pred)]
        print('    会合面 vs 解析 locus: %d 层, 平均偏差 %.2f 胞, 最大 %.2f 胞' % (
            len(d), float(np.mean(d)), float(np.max(d))))
        print('    会合面 y 随高度: ' + ' '.join('%d:%.1f' % (y[0], y[1] + 0.5) for y in yb[::max(1, len(yb)//8)]))
    out[mode] = dict(n1=n1, n2=n2, nst=nst, wall=wall,
                     gb_err=float(np.mean(d)) if (yb and pred) else None)
json.dump(out, open('/mnt/f/speed_up/bench/exaca/mirror_result.json', 'w'), indent=1)