#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_verify_physics_check.py --- 结果是不是"物理的"？两个量化检验

A) 现有熔池演示的晶粒图，与【同一批种子的静态各向异性 Voronoi】差多少？
   （若几乎相同 ⇒ 该结果其实是几何镶嵌，不是"生长竞争"的产物）
B) 把冷却放慢（τ 增大）⇒ 让 CA 自己的包络推进主导 ⇒ 看：
   - 热约束归属占比是否降下来
   - 存活晶粒的 <100> 轴是否系统性地更靠近温度梯度方向（Walton-Chalmers 择优）
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ca3d import CA3D, IRF, T_LIQ, T_SOL
from scipy import ndimage as ndi
from scipy.cluster.vq import kmeans2

DX = 3.0e-6; NX, NY, NZ = 67, 100, 67
T_PEAK, SIGMA, TAU0, T_BATH = 2600.0, 90e-6, 3.0e-4, 353.0
NSEED = 3


def build(tau, seed=2026, pct=90.0):
    ca = CA3D(NX, NY, NZ, DX, irf=IRF(), seed=seed, capture="envelope", lg_percentile=pct)
    T0 = ca.T_meltpool(T_PEAK, SIGMA, TAU0, T_BATH)
    poolT = T0 > T_SOL
    wall = ndi.binary_dilation(poolT) & ~poolT
    zbot = np.nonzero(poolT.sum(axis=(0, 1)))[0].min()
    foot = wall.copy(); foot[:, :, zbot+3:] = False
    wc = np.argwhere(foot).astype(float)
    _cen, lab = kmeans2(wc, NSEED, minit="++", seed=4)
    seedpos = []
    for k in range(NSEED):
        idx = wc[lab == k]; i, j, kk = idx[len(idx)//2].astype(int)
        ca.add_grain(int(i), int(j), int(kk)); seedpos.append((int(i), int(j), int(kk)))
    ca.seed_solid_from_substrate(T0, T_SOL)
    pool0 = (ca.gid == 0).copy()
    V_max = float(ca.irf(np.array([T_LIQ - T_SOL]))[0]); dt = DX/(4*V_max)
    s = 0
    for s in range(int(1.2e-2/dt)):
        ca.t = s*dt
        ca.step(dt, ca.T_meltpool(T_PEAK, SIGMA, tau, T_BATH), window=None)
        if (ca.gid == 0).sum() == 0:
            break
    ca.finalize_chemistry()
    return ca, pool0, seedpos, s, dt


def voronoi_map(ca, pool0, seedpos):
    """同一批种子的静态各向异性 Voronoi（argmin sup，平局按 gid 小）"""
    ti = np.argwhere(pool0 & (ca.gid > 0))
    best = np.full(len(ti), np.inf); bg = np.full(len(ti), 1 << 30, np.int64)
    for k, (i, j, kk) in enumerate(seedpos, start=1):
        sup = ca.envelope_sup(k, ti[:, 0], ti[:, 1], ti[:, 2])
        upd = (sup < best) | ((sup == best) & (k < bg))
        best[upd] = sup[upd]; bg[upd] = k
    m = np.zeros(ca.shape, np.int32)
    m[ti[:, 0], ti[:, 1], ti[:, 2]] = bg
    return m


print("=" * 100)
print("A) 现有演示结果 vs 静态各向异性 Voronoi（同一批种子）")
print("=" * 100)
ca, pool0, seedpos, s, dt = build(TAU0)
pool = pool0 & (ca.gid > 0)
vmap = voronoi_map(ca, pool0, seedpos)
d = int((vmap[pool] != ca.gid[pool]).sum())
print("  种子位置(池底 footprint): %s" % (seedpos,))
print("  池内胞 %d; 与静态 Voronoi 不同的胞 %d (%.2f%%)  => %s" % (
    pool.sum(), d, 100.0*d/pool.sum(),
    "几乎就是几何镶嵌" if d/pool.sum() < 0.05 else "生长竞争起了作用"))
print("  热约束归属占比 %.0f%%  (n_thermal=%d/%d)" % (
    100.0*getattr(ca, "n_thermal", 0)/pool0.sum(), getattr(ca, "n_thermal", 0), pool0.sum()))

print()
print("=" * 100)
print("B) 冷却放慢（τ 增大）⇒ 让 CA 包络推进主导；看存活晶粒的取向择优")
print("=" * 100)
X, Y, Z = ca.coords()
print("   τ(s)      步数  热归属占比  池内晶粒数/占比            存活大晶粒的 <100> 对梯度的对齐 (cos)")
for tau in (3.0e-4, 1.0e-3, 3.0e-3):
    ca2, pool02, seedpos2, s2, dt2 = build(tau)
    pool2 = pool02 & (ca2.gid > 0)
    u, c = np.unique(ca2.gid[pool2], return_counts=True)
    # 每个晶粒的取向 vs 该晶粒所在区域的平均梯度方向
    gz, gy, gx = np.gradient(ca2.T_meltpool(T_PEAK, SIGMA, tau, T_BATH), DX)
    al = []
    for gid in u:
        m = pool2 & (ca2.gid == gid)
        if m.sum() < 50:
            continue
        gvec = np.array([gx[m].mean(), gy[m].mean(), gz[m].mean()])
        nrm = np.linalg.norm(gvec)
        if nrm < 1e-12:
            al.append((int(gid), int(m.sum()), np.nan)); continue
        gvec /= nrm
        P = ca2.axes[gid]
        cosmax = max(abs(float(P[:, a] @ gvec)) for a in range(3))
        al.append((int(gid), int(m.sum()), cosmax))
    frac = " ".join("%d:%.0f%%" % (a, 100.0*b/pool2.sum()) for a, b in zip(u, c) if a > 0)
    print("   %-8.1e %5d  %5.0f%%      %-30s %s" % (
        tau, s2, 100.0*getattr(ca2, "n_thermal", 0)/pool02.sum(), frac,
        " ".join("g%d(%.2f)" % (g, cc) for g, n_, cc in al)))
print()
print("   说明: cos 越接近 1 = 该晶粒的某个 <100> 晶轴越平行于它所在处的温度梯度。")
print("   Walton-Chalmers 择优要求【存活下来的大晶粒】系统性地比被吞掉的晶粒 cos 更大。")