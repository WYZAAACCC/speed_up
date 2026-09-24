#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_wc_envelope.py --- 决定性检验：新默认(envelope)下，晶粒生长是否有【取向择优淘汰】

设定：定向凝固（竖直梯度 G=1e6 K/m，抽拉 0.02 m/s），液相保持在固相线之上（T_LIQ-16K）
     ⇒ 热约束一胞都不参与（n_thermal=0）⇒ 晶粒图 100% 由 CA 自己的包络推进决定。
    9 个种子沿底面排开、随机取向，长到 ≈1.5 个间距（让竞争/淘汰有时间发生）。
判据：① 占据最终前沿(顶部)的晶粒数应远少于 9（错取向被挤掉）
     ② 存活晶粒的 <100> 对 +z 的对齐 cos 应系统性更大
     ③ 存活晶粒应沿 +z 拉长（长径比 > 1，prior-β 柱状晶的定性特征）
"""
import os, sys, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi

NX, NY, NZ = 80, 80, 200
DX = 2.0e-6
G = 1.0e6
VPULL = 0.02
DT_K = 16.0            # 液相过冷度: T = T_LIQ - 16 = 1895.1 K > T_SOL=1893.2 ⇒ 不触发热约束
NSEED = 9


def run(capture="envelope", seed=11, nst=340, dTu=DT_K):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=seed, capture=capture)
    rng = np.random.default_rng(seed)
    xs = np.linspace(8, NX-9, 3).astype(int)
    ys = np.linspace(8, NY-9, 3).astype(int)
    seeds = []
    for i in xs:
        for j in ys:
            g = ca.add_grain(int(i), int(j), 0, quat=tuple(rng.normal(size=4)))
            seeds.append((g, (int(i), int(j))))
    V = float(ca.irf(np.array([dTu]))[0])
    dt = DX/(4*V)
    for s in range(nst):
        ca.t = s*dt
        # 液相处在 T_LIQ-dTu；抽拉把等温线向上推
        T = T_LIQ - dTu + G*(np.arange(NZ)[None, None, :]*DX - VPULL*ca.t)
        T = np.broadcast_to(T, ca.shape).copy()
        ca.step(dt, T, window="full")
    return ca, seeds, dt


print("=" * 100)
print("定向凝固 + 9 个随机取向种子（热约束零参与）—— 取向择优淘汰检验")
print("=" * 100)
for cap in ("envelope", "decentered"):
    ca, seeds, dt = run(cap)
    g = ca.gid
    n_th = getattr(ca, "n_thermal", 0)
    # 最终前沿 = 每个 (i,j) 列上最高的实心胞
    front_gids = []
    for i in range(NX):
        for j in range(NY):
            col = g[i, j, :]
            k = np.nonzero(col > 0)[0]
            if len(k):
                front_gids.append(int(col[k[-1]]))
    keep, cnt = np.unique(front_gids, return_counts=True)
    # 每个晶粒: 体积 + 垂直于生长方向的最大截面 + 长径比
    rows = []
    for gid, (_, (si, sj)) in zip([s[0] for s in seeds], seeds):
        m = (g == gid)
        n = int(m.sum())
        if n == 0:
            rows.append((gid, 0, 0, np.nan, np.nan)); continue
        kz = np.nonzero(m.sum(axis=(0, 1)))[0]
        h = kz[-1] - kz[0] + 1
        # 宽度 = 最大水平截面积等效直径
        area = int(m.sum(axis=2).max())
        w = math.sqrt(max(area, 1))
        rows.append((gid, n, h, w, h/max(w, 1e-9)))
    # 取向对齐 cos（<100> 与 +z）
    P = {s[0]: ca.axes[s[0]] for s in seeds}
    print("\n--- capture = %s   (热约束归属 %d 胞 ⇒ %s)" % (
        cap, n_th, "CA 自己说了算" if n_th == 0 else "热约束参与了"))
    print("   晶粒  体积    高(胞)  等效宽   长径比   cos(<100>,+z)   占前沿列数")
    for gid, n, h, w, ar in rows:
        cz = max(abs(float(P[gid][2, a])) for a in range(3))
        cntf = int(cnt[np.where(keep == gid)[0][0]]) if gid in keep else 0
        print("   %3d  %6d  %5d  %6.1f  %7.2f      %.3f           %4d" % (
            gid, n, h, w, ar, cz, cntf))
    # 存活 vs 对齐的相关性（占前沿列数 > 0 的算存活）
    al = np.array([max(abs(float(P[gid][2, a])) for a in range(3)) for gid, *_ in rows])
    alive = np.array([1.0 if (gid in keep and cnt[np.where(keep == gid)[0][0]] > 0) else 0.0
                      for gid, *_ in rows])
    vol = np.array([n for _, n, *_ in rows], float)
    print("   存活(占前沿)晶粒数 = %d / %d;  mean cos | 存活 %.3f vs 被淘汰 %.3f" % (
        int(alive.sum()), len(rows), float(al.mean() if alive.mean() in (0, 1) else
        (al[alive > 0].mean())), float(al[alive == 0].mean() if (alive == 0).any() else np.nan)))
    if alive.std() > 0 and len(alive) > 2:
        print("   corr(cos, 占前沿列数=存活) = %+.3f ;  corr(cos, 体积) = %+.3f" % (
            float(np.corrcoef(al, alive)[0, 1]), float(np.corrcoef(al, vol)[0, 1])))