#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_texture_compare2.py --- 严格对比：只用【基底晶粒】（正 ID，可从取向表直接算），尺寸加权 min∠'''
import os, json
import numpy as np
D = '/mnt/f/speed_up/bench/exaca'
RUN = '/root/bench/run'
N = 20
VECS = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1).reshape(-1, 3, 3)


def mangle(P):
    c = np.abs(P[:, 2]) / np.linalg.norm(P, axis=1)
    return np.degrees(np.arccos(np.clip(c.max(), 0, 1)))


def parse_vtk(fp, field):
    lines = open(fp).readlines()
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith('SCALARS') and field.lower() in ln.lower():
            vals = []; j = i + 2
            while j < len(lines):
                t = lines[j].strip()
                if not t or t[0].isalpha():
                    break
                vals += [float(x) for x in t.split()]; j += 1
            return np.array(vals)
    raise RuntimeError('no field')


pop = np.mean([mangle(VECS[k]) for k in range(0, 10000, 7)])
print('取向表全体 min∠ 均值 = %.2f°（随机取向基准）' % pop)
print()
print('%-34s %-8s %-12s %-12s' % ('', '晶粒数', '基底加权', '基底不加权'))
res = {}
for seed in range(5):
    g = parse_vtk(os.path.join(RUN, 'Exa_seed%d.vtk' % seed), 'GrainID').astype(int)
    ids, cnt = np.unique(g[g > 0], return_counts=True)          # 只取基底（正 ID）
    ang = np.array([mangle(VECS[i - 1]) for i in ids])
    w = cnt / cnt.sum()
    res[seed] = float((ang * w).sum())
    print('ExaCA  seed %d                     %-8d %.2f°      %.2f°' % (
        seed, len(ids), res[seed], ang.mean()))
print('  ExaCA 基底加权均值 = %.2f°' % np.mean(list(res.values())))
print()
m = json.load(open(D + '/mine_stats.json'))
print('我方（同一取向表，基底 = 100 个位点里的存活者）:')
for x in m:
    print('  seed %d: 基底加权 %.2f°  不加权 %.2f°' % (x['seed'], x['ang_w_sub'], x['ang_simple']))
print('  我方基底加权均值 = %.2f°' % np.mean([x['ang_w_sub'] for x in m]))