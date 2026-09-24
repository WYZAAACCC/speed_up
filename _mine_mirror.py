#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_mine_mirror.py --- 在 ExaCA Inp_SmallDirSolidification 的【完全相同约定】下跑我的 CA
约定（全部照抄 ExaCA 源码）:
  dx=1µm, 20^3, dt=6.6667e-8 s, 3000 步
  ΔT(z,t) = G (R t − z dx),  G=5e5 K/m, R=3e5 µm/s
  IRF = ExaCA Inconel625 三次律（不封顶）
  底面 25% 位点 = 100 个基底晶粒（随机位置 + 随机取向，取向表 GrainOrientationVectors.csv）
  形核: n_max = 250e12 /m^3 => 期望 2 个位点; 位置均匀随机; 过冷度 ~ N(5, 0.5) K; 局部 ΔT 达到该值时激活
'''
import os, sys, math, json
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, T_LIQ

A, B, C = -1.0302e-7, 1.0533e-4, 2.2196e-3
DX, N, G, R = 1.0e-6, 20, 5.0e5, 3.0e5      # R = 冷却速率 [K/s]（ExaCA 约定）
DT = 0.0666667e-6
NSTEP = 3000
SUBN, NMAX = 0.25, 250e12
D = '/mnt/f/speed_up/bench/exaca'
VECS = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1)
VECS = VECS.reshape(-1, 3, 3)          # 每行 9 个数 = 3 个晶轴（完整取向基）
print('取向表: %d 条取向（每条 3 个正交单位向量）' % len(VECS))


class CubicIRF(object):
    def __init__(self):
        self.dT_lo = 0.0; self.dT_hi = 1e4
        self.V_at_hi = A * 1e4 ** 3 + B * 1e4 ** 2 + C * 1e4
    def __call__(self, dT):
        dT = np.asarray(dT, float)
        return np.clip(A * dT ** 3 + B * dT ** 2 + C * dT, 0.0, None)
    def capped(self, dT):
        dT = np.asarray(dT, float)
        n_low = int(np.count_nonzero(dT < 0.0))
        v = np.clip(A * np.maximum(dT, 0) ** 3 + B * np.maximum(dT, 0) ** 2 +
                    C * np.maximum(dT, 0), 0.0, None)
        return v, np.maximum(dT, 0.0), n_low, 0


def quat_from_P(P):
    P = P / np.linalg.norm(P[:, 0]) if P.shape == (3, 3) else P
    tr = P[0, 0] + P[1, 1] + P[2, 2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return (0.25 * s, (P[2, 1] - P[1, 2]) / s, (P[0, 2] - P[2, 0]) / s, (P[1, 0] - P[0, 1]) / s)
    if P[0, 0] > P[1, 1] and P[0, 0] > P[2, 2]:
        s = math.sqrt(1.0 + P[0, 0] - P[1, 1] - P[2, 2]) * 2
        return ((P[2, 1] - P[1, 2]) / s, 0.25 * s, (P[0, 1] + P[1, 0]) / s, (P[0, 2] + P[2, 0]) / s)
    if P[1, 1] > P[2, 2]:
        s = math.sqrt(1.0 + P[1, 1] - P[0, 0] - P[2, 2]) * 2
        return ((P[0, 2] - P[2, 0]) / s, (P[0, 1] + P[1, 0]) / s, 0.25 * s, (P[1, 2] + P[2, 1]) / s)
    s = math.sqrt(1.0 + P[2, 2] - P[0, 0] - P[1, 1]) * 2
    return ((P[1, 0] - P[0, 1]) / s, (P[0, 2] + P[2, 0]) / s, (P[1, 2] + P[2, 1]) / s, 0.25 * s)


def run(seed, mode='envelope', pct=90.0, thermal_off=False):
    rng = np.random.default_rng(seed)
    irf = CubicIRF()
    ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode, lg_percentile=pct)
    if thermal_off:
        ca.allow_spont = False        # 关掉 T<T_SOL 的强制归属（ExaCA 没有这条规则）
    # --- 基底: 100 个随机底面胞 + 随机取向
    nsub = int(round(SUBN * N * N))
    seed_gids = []
    for _ in range(nsub):
        # ExaCA: 连续均匀分布再取整 => 允许两个位点落在同一个胞（它自己的注释也承认会低估密度）
        x = rng.uniform(-0.49999, N - 0.5); y = rng.uniform(-0.49999, N - 0.5)
        i = int(min(max(math.floor(x), 0), N - 1)); j = int(min(max(math.floor(y), 0), N - 1))
        Pp = VECS[rng.integers(len(VECS))]
        g = ca.add_grain(i, j, 0, quat=quat_from_P(Pp))
        seed_gids.append(g)
    # --- 形核位点: 期望 n_max*V
    vol = (N * DX) ** 3
    nexp = NMAX * vol
    nnuc = int(np.round(nexp))
    nuc = []
    for _ in range(nnuc):
        i = int(rng.integers(N)); j = int(rng.integers(N)); k = int(rng.integers(N))
        dTn = float(rng.normal(5.0, 0.5))
        nuc.append([i, j, k, dTn, False])
    z = np.arange(N)
    gids_of_nuc = []
    for s in range(NSTEP):
        t = s * DT
        # ★ 修正: ExaCA 的 R 是【冷却速率 K/s】; ΔT(z,t) = R*t - G*z_phys, z_phys=(z+0.5)dx
        dTfield = R * t - G * (z + 0.5) * DX               # ΔT(z,t) [K]
        T = T_LIQ - dTfield[None, None, :]
        T = np.broadcast_to(T, ca.shape).copy()
        for nn in nuc:
            if nn[4]:
                continue
            if dTfield[nn[2]] >= nn[3] and ca.gid[nn[0], nn[1], nn[2]] == 0:
                Pp = VECS[rng.integers(len(VECS))]
                g = ca.add_grain(nn[0], nn[1], nn[2], quat=quat_from_P(Pp))
                nn[4] = True
                gids_of_nuc.append(g)
        ca.step(DT, T, window='full')
    gg = ca.gid
    ids, cnt = np.unique(gg[gg > 0], return_counts=True)
    tot = int(cnt.sum())
    nucset = set(gids_of_nuc)
    frac = float(sum(c for g, c in zip(ids, cnt) if g in nucset)) / tot
    def mang(g):
        Pm = ca.axes[g]
        c = np.abs(Pm[2, :]) / np.linalg.norm(Pm, axis=0)
        return float(np.degrees(np.arccos(np.clip(c.max(), 0, 1))))
    # 尺寸加权的 min_angle（与 ExaCA 侧同一算法）
    ang = np.array([mang(g) for g in ids])
    w = cnt / cnt.sum()
    nucmask = np.array([g in nucset for g in ids])
    return dict(seed=seed, n_grain=len(ids), n_nuke=len(gids_of_nuc), frac_nuke=frac,
                mean_size=float(cnt.mean()), max_size=int(cnt.max()), tot=tot,
                ang_w=float((ang * w).sum()), ang_simple=float(ang.mean()),
                ang_w_sub=float((ang[~nucmask] * w[~nucmask]).sum() / max(w[~nucmask].sum(), 1e-9)),
                ang_w_nuc=float((ang[nucmask] * w[nucmask]).sum() / max(w[nucmask].sum(), 1e-9))
                if nucmask.any() else None)


print()
print('B) 我的 CA（同约定：20^3, dx=1µm, dt=6.67e-8s, 3000 步, ExaCA 的 In625 三次律, 100 基底位点, 期望 2 个形核位点）')
out = []
for seed in (0, 1, 2, 3, 4):
    r = run(seed)
    out.append(r)
    print('  seed %d: 晶粒数 %3d, 形核晶粒 %d 个, 形核占比 %.3f, 平均晶粒 %6.1f 胞' % (
        seed, r['n_grain'], r['n_nuke'], r['frac_nuke'], r['mean_size']))
print('  ------ 我方汇总: 晶粒数 %.1f±%.1f, 形核占比 %.3f±%.3f, 平均晶粒 %.1f±%.1f 胞' % (
    np.mean([e['n_grain'] for e in out]), np.std([e['n_grain'] for e in out]),
    np.mean([e['frac_nuke'] for e in out]), np.std([e['frac_nuke'] for e in out]),
    np.mean([e['mean_size'] for e in out]), np.std([e['mean_size'] for e in out])))
print()
print('D) 关掉"热力学约束归属"（对齐 ExaCA）后重跑，看择优/形核占比是否向 ExaCA 靠拢:')
for seed in (0, 1, 2, 3, 4):
    r = run(seed, thermal_off=True)
    print('  seed %d: 晶粒数 %3d, 形核占比 %.3f, 基底加权 min∠ %.2f°' % (
        seed, r['n_grain'], r['frac_nuke'], r['ang_w_sub']))
print()
print('C) 集总敏感度（lg_percentile 50/90/100，同 5 个种子）——查"形核占比偏高"是否来自单-ℓ 集总')
for pct in (50.0, 90.0, 100.0):
    rs = [run(sd, pct=pct) for sd in (0, 1, 2)]
    print('  pct=%-5g 晶粒数 %.1f, 形核占比 %.3f±%.3f, 平均晶粒 %.1f 胞' % (
        pct, np.mean([x['n_grain'] for x in rs]), np.mean([x['frac_nuke'] for x in rs]),
        np.std([x['frac_nuke'] for x in rs]), np.mean([x['mean_size'] for x in rs])))
json.dump(out, open(D + '/mine_stats.json', 'w'), indent=1)