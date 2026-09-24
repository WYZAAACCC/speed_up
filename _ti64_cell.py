#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_ti64_cell.py --- 用 capture="cell" 跑 Ti64 同一对照（20 种子），与 ExaCA 旧结果对比'''
import os, sys, json, math, re
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, T_LIQ
from scipy import stats
RUN = '/root/bench/run'
D = '/mnt/f/speed_up/bench/exaca'
N, DX, G, R, DT_S, NSTEP = 20, 1.0e-6, 5.0e5, 3.0e5, 0.0666667e-6, 2000
TAB = np.loadtxt(RUN + '/irf_ti64_table.csv', delimiter=',', skiprows=1)
VEC = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1).reshape(-1, 3, 3)


class TableIRF(object):
    def __init__(self):
        self.dT_lo = float(TAB[:, 0].min()); self.dT_hi = float(TAB[:, 0].max())
        self.V_at_hi = float(TAB[-1, 1])
    def __call__(self, dT):
        return np.interp(dT, TAB[:, 0], TAB[:, 1], left=TAB[0, 1], right=TAB[-1, 1])
    def capped(self, dT):
        dT = np.asarray(dT, float)
        n_low = int(np.count_nonzero(dT < self.dT_lo))
        return (np.interp(dT, TAB[:, 0], TAB[:, 1], left=TAB[0, 1], right=TAB[-1, 1]),
                np.clip(dT, self.dT_lo, self.dT_hi), n_low, 0)


def q_from_P(P):
    tr = P[0,0]+P[1,1]+P[2,2]
    if tr > 0:
        s = math.sqrt(tr+1)*2
        return (0.25*s, (P[2,1]-P[1,2])/s, (P[0,2]-P[2,0])/s, (P[1,0]-P[0,1])/s)
    if P[0,0] > P[1,1] and P[0,0] > P[2,2]:
        s = math.sqrt(1+P[0,0]-P[1,1]-P[2,2])*2
        return ((P[2,1]-P[1,2])/s, 0.25*s, (P[0,1]+P[1,0])/s, (P[0,2]+P[2,0])/s)
    if P[1,1] > P[2,2]:
        s = math.sqrt(1+P[1,1]-P[0,0]-P[2,2])*2
        return ((P[0,2]-P[2,0])/s, (P[0,1]+P[1,0])/s, 0.25*s, (P[1,2]+P[2,1])/s)
    s = math.sqrt(1+P[2,2]-P[0,0]-P[1,1])*2
    return ((P[1,0]-P[0,1])/s, (P[0,2]+P[2,0])/s, (P[1,2]+P[2,1])/s, 0.25*s)


def mangle(P):
    c = np.abs(P[2, :]) / np.linalg.norm(P, axis=0)
    return float(np.degrees(np.arccos(np.clip(c.max(), 0, 1))))


def run_mine(seed, mode, tiebreak='ratio'):
    rng = np.random.default_rng(seed)
    ca = CA3D(N, N, N, DX, irf=TableIRF(), seed=seed+1, capture=mode)
    ca.allow_spont = False
    ca.cell_tiebreak = tiebreak
    for _ in range(int(round(0.25*N*N))):
        x = rng.uniform(-0.49999, N-0.5); y = rng.uniform(-0.49999, N-0.5)
        ca.add_grain(int(min(max(math.floor(x),0),N-1)), int(min(max(math.floor(y),0),N-1)),
                     0, quat=q_from_P(VEC[rng.integers(len(VEC))]))
    nuc = [[int(rng.integers(N)), int(rng.integers(N)), int(rng.integers(N)),
            float(rng.normal(5.0,0.5)), False] for _ in range(2)]
    z = np.arange(N); gn = []
    for s in range(NSTEP):
        t = s*DT_S
        dT = R*t - G*(z+0.5)*DX
        T = np.broadcast_to((T_LIQ - dT)[None,None,:], ca.shape).copy()
        for nn in nuc:
            if not nn[4] and dT[nn[2]] >= nn[3] and ca.gid[nn[0],nn[1],nn[2]] == 0:
                gn.append(ca.add_grain(nn[0],nn[1],nn[2], quat=q_from_P(VEC[rng.integers(len(VEC))])))
                nn[4] = True
        ca.step(DT_S, T, window='full')
    g = ca.gid
    ids, cnt = np.unique(g[g > 0], return_counts=True)
    nucs = set(gn)
    sub = np.array([x not in nucs for x in ids])
    ang = np.array([mangle(ca.axes[int(x)]) for x in ids])
    w = cnt/cnt.sum()
    return dict(n_grain=len(ids), n_nuke=len(gn), frac_nuke=float(cnt[~sub].sum())/int(cnt.sum()),
                mean_size=float(cnt.mean()), tot=int(cnt.sum()),
                ang_w_sub=float((ang[sub]*w[sub]).sum()/max(w[sub].sum(),1e-9)))


# ExaCA 结果从旧日志解析
txt = open('/mnt/f/speed_up/_ti64_cmp.log', encoding='utf-8').read()
E = np.array([[float(x) for x in m.groups()] for m in re.finditer(
    r'ExaCA\s+seed\s+\d+: 晶粒\s+(\d+), 形核 (\d+), 形核占比 ([\d.]+), 平均 ([\d.]+) 胞, 基底加权 min∠ ([\d.]+)', txt)])
print('ExaCA (n=%d) 已就绪' % len(E))
mine = {'cell': [run_mine(s, 'cell') for s in range(20)],
        'envelope': [run_mine(s, 'envelope') for s in range(20)],
        'cell_fc': [run_mine(s, 'cell', 'firstcome') for s in range(20)]}
print()
print('%-16s %-16s %-16s %-16s %-9s' % ('指标', 'ExaCA', '我方 cell', '我方 envelope', 'cell/ExaCA'))
for k, nm in (('n_grain','晶粒数'), ('mean_size','平均晶粒(胞)'), ('tot','固相胞数'),
              ('frac_nuke','形核占比'), ('ang_w_sub','基底加权 min∠')):
    a = E[:, 0] if k=='n_grain' else (E[:,3] if k=='mean_size' else (None if k=='tot' else
        (E[:,2] if k=='frac_nuke' else E[:,4])))
    if k == 'tot':
        a = E[:,0]*E[:,3]
    b = np.array([x[k] for x in mine['cell']]); c = np.array([x[k] for x in mine['envelope']])
    d = np.array([x[k] for x in mine['cell_fc']])
    rel = 100*(b.mean()-a.mean())/a.mean()
    t, p = stats.ttest_ind(b, a, equal_var=False)
    relfc = 100*(d.mean()-a.mean())/a.mean()
    print('%-14s %-12s %-12s %-12s %-12s %+8.1f%%  (firstcome %+.1f%%)' % (
        nm, '%.2f' % a.mean(), '%.2f' % b.mean(), '%.2f' % c.mean(), '%.2f' % d.mean(), rel, relfc))