#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_diag_nucleated.py --- 定位"形核占比差 2×"：比较形核晶粒的胞数/高度/质心（两边都取 20³ 算例）'''
import json, os, sys, glob
import numpy as np
RUN = '/root/bench/run'
D = '/mnt/f/speed_up/bench/exaca'


def parse_vtk(fp, field='GrainID'):
    lines = open(fp).readlines()
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith('SCALARS') and field.lower() in ln.lower():
            vals = []
            j = i + 2
            while j < len(lines):
                t = lines[j].strip()
                if not t or t[0].isalpha():
                    break
                vals += [int(float(x)) for x in t.split()]
                j += 1
            return np.array(vals)
    raise RuntimeError('no field')


N = 20
print('ExaCA 侧（形核晶粒 = 负 ID）:')
for seed in (0, 1, 2, 3, 4):
    fp = os.path.join(RUN, 'Exa_seed%d.vtk' % seed)
    if not os.path.exists(fp):
        continue
    g = parse_vtk(fp)
    assert len(g) == N ** 3, len(g)
    g = g.reshape((N, N, N), order='F')      # VTK 结构化点: x 最快
    neg = np.unique(g[g < 0])
    tot = int((g > 0).sum() + (g < 0).sum())
    info = []
    for nid in neg:
        m = (g == nid)
        zr = np.nonzero(m.any(axis=(0, 1)))[0]
        yy, xx = np.nonzero(m.any(axis=2))
        info.append('id%d: %4d 胞, z=%d..%d, 质心(x,y,z)=(%.0f,%.0f,%.0f)' % (
            nid, int(m.sum()), zr[0], zr[-1], xx.mean(), yy.mean(),
            np.nonzero(m)[2].mean()))
    frac = 100.0 * (g < 0).sum() / tot
    print('  seed %d: 形核占比 %.1f%%; %s' % (seed, frac, '; '.join(info)))
print()
print('我方（形核晶粒 = 运行中记录的 seed_gids 之外的 nuclei）:')
mine = json.load(open(D + '/mine_stats.json'))
for r in mine:
    print('  seed %d: 形核占比 %.1f%%, 形核 %d 个, 总晶粒 %d' % (
        r['seed'], 100 * r['frac_nuke'], r['n_nuke'], r['n_grain']))