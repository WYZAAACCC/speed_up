#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_ti64_compare.py --- Ti64（LKT 查表，两码逐点相同）同初始条件对比
ExaCA: Inp_SmallDirSolidification 的其它参数不变，只把材料换成 Ti64.json(table)
我方  : 同一套约定 + TableIRF(同一 CSV) ；关掉热力学约束归属(ExaCA 没有该规则)
'''
import os, sys, json, math, subprocess, glob
import numpy as np
sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
from ca3d import CA3D, T_LIQ
RUN = '/root/bench/run'
EXA = '/root/bench/ExaCA-master/build/bin/ExaCA'
D = '/mnt/f/speed_up/bench/exaca'
N, DX, G, R, DT_S, NSTEP = 20, 1.0e-6, 5.0e5, 3.0e5, 0.0666667e-6, 2000
CSV = RUN + '/irf_ti64_table.csv'
TAB = np.loadtxt(CSV, delimiter=',', skiprows=1)
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


def mangle(P):
    c = np.abs(P[2, :]) / np.linalg.norm(P, axis=0)
    return float(np.degrees(np.arccos(np.clip(c.max(), 0, 1))))


def run_exaca(seed):
    base = json.load(open(D + '/Inp_SmallDirS_abs.json'))
    base['MaterialFileName'] = RUN + '/Ti64.json'
    base['RandomSeed'] = seed
    base['Printing'] = dict(base['Printing'], OutputFile='Ti_seed%d' % seed)
    p = RUN + '/Inp_Ti%d.json' % seed
    json.dump(base, open(p, 'w'), indent=1)
    subprocess.run([EXA, p], cwd=RUN, capture_output=True, text=True)
    fp = RUN + '/Ti_seed%d.vtk' % seed
    if not os.path.exists(fp):
        return None
    return fp


def parse_vtk(fp, field='GrainID'):
    lines = open(fp).readlines()
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith('SCALARS') and field.lower() in ln.lower():
            vals = []; j = i + 2
            while j < len(lines):
                t = lines[j].strip()
                if not t or t[0].isalpha():
                    break
                vals += [int(float(x)) for x in t.split()]; j += 1
            return np.array(vals)
    raise RuntimeError('no field')


def run_mine(seed, thermal_off=True, mode='envelope'):
    rng = np.random.default_rng(seed)
    irf = TableIRF()
    ca = CA3D(N, N, N, DX, irf=irf, seed=seed + 1, capture=mode)
    if thermal_off:
        ca.allow_spont = False
    for _ in range(int(round(0.25 * N * N))):
        x = rng.uniform(-0.49999, N - 0.5); y = rng.uniform(-0.49999, N - 0.5)
        i = int(min(max(math.floor(x), 0), N - 1)); j = int(min(max(math.floor(y), 0), N - 1))
        ca.add_grain(i, j, 0, quat=q_from_P(VEC[rng.integers(len(VEC))]))
    nuc = []
    for _ in range(2):
        nuc.append([int(rng.integers(N)), int(rng.integers(N)), int(rng.integers(N)),
                    float(rng.normal(5.0, 0.5)), False])
    z = np.arange(N); gn = []
    for s in range(NSTEP):
        t = s * DT_S
        dT = R * t - G * (z + 0.5) * DX      # ExaCA: ΔT = R·t − G·z_phys（R=冷却速率 K/s）
        T = np.broadcast_to((T_LIQ - dT)[None, None, :], ca.shape).copy()
        for nn in nuc:
            if not nn[4] and dT[nn[2]] >= nn[3] and ca.gid[nn[0], nn[1], nn[2]] == 0:
                gn.append(ca.add_grain(nn[0], nn[1], nn[2], quat=q_from_P(VEC[rng.integers(len(VEC))])))
                nn[4] = True
        ca.step(DT_S, T, window='full')
    g = ca.gid
    ids, cnt = np.unique(g[g > 0], return_counts=True)
    nucs = set(gn)
    sub = np.array([x not in nucs for x in ids])
    ang = np.array([mangle(ca.axes[int(x)]) for x in ids])
    w = cnt / cnt.sum()
    return dict(n_grain=len(ids), n_nuke=len(gn), frac_nuke=float(cnt[~sub].sum()) / int(cnt.sum()),
                mean_size=float(cnt.mean()),
                ang_w_sub=float((ang[sub] * w[sub]).sum() / max(w[sub].sum(), 1e-9)))


print('Ti64 材料: ExaCA/Ti64.json = {"function":"table", dT %.3f..%.3f K, 逐点取自 irf_ti64.csv}' % (
    TAB[0, 0], TAB[-1, 0]))
print()
exa = []
for s in range(20):
    fp = run_exaca(s)
    if fp is None:
        print('  ExaCA seed %d 失败' % s); continue
    g = parse_vtk(fp)
    ids, cnt = np.unique(g[g > 0], return_counts=True)
    nk = (g < 0)
    sub = np.array([mangle(VEC[i - 1]) for i in ids])
    w = cnt / cnt.sum()
    exa.append(dict(n_grain=len(ids), n_nuke=len(np.unique(g[g < 0])),
                    frac_nuke=float(nk.sum()) / int((g != 0).sum()),
                    mean_size=float(cnt.mean()), ang_w_sub=float((sub * w).sum())))
    print('  ExaCA seed %d: 晶粒 %3d, 形核 %d, 形核占比 %.3f, 平均 %.1f 胞, 基底加权 min∠ %.2f°' % (
        s, exa[-1]['n_grain'], exa[-1]['n_nuke'], exa[-1]['frac_nuke'],
        exa[-1]['mean_size'], exa[-1]['ang_w_sub']))
mine = [run_mine(s) for s in range(20)]
for s, r in enumerate(mine):
    print('  我方   seed %d: 晶粒 %3d, 形核 %d, 形核占比 %.3f, 平均 %.1f 胞, 基底加权 min∠ %.2f°' % (
        s, r['n_grain'], r['n_nuke'], r['frac_nuke'], r['mean_size'], r['ang_w_sub']))
print()
print('%-10s %-22s %-22s' % ('指标', 'ExaCA (Ti64 表)', '我方 (Ti64 表)'))
for k, nm in (('n_grain', '晶粒数'), ('mean_size', '平均晶粒(胞)'), ('frac_nuke', '形核占比'),
              ('ang_w_sub', '基底加权 min∠(°)')):
    a = np.mean([x[k] for x in exa]); b = np.mean([x[k] for x in mine])
    print('%-10s %-22s %-22s  相对差 %+.1f%%' % (nm, '%.3f' % a, '%.3f' % b, 100 * (b - a) / a))