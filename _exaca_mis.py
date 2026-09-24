#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_misorient_vs_mine.py --- 用 ExaCA 输出的 GrainMisorientation 做定量对比
ExaCA 的 _Misorientations.vtk 存的是每个胞的"该晶粒 <100> 与 +Z 的夹角(度)"。
对比: (a) 全体固相按尺寸加权的平均取向差;  (b) 形核晶粒(GrainID<0)的取向差。
'''
import os, json, glob
import numpy as np
RUN = '/root/bench/run'
N = 20


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
    raise RuntimeError('no field %s in %s' % (field, fp))


print('=== ExaCA（5 个种子）')
exa_all, exa_nuc = [], []
for seed in range(5):
    g = parse_vtk(os.path.join(RUN, 'Exa_seed%d.vtk' % seed), 'GrainID')
    m = parse_vtk(os.path.join(RUN, 'Exa_seed%d_Misorientations.vtk' % seed), 'GrainMisorientation')
    if len(g) != N ** 3 or len(m) != N ** 3:
        print('  seed %d: 长度异常 %d/%d' % (seed, len(g), len(m))); continue
    sol = g != 0
    a = m[sol].mean()
    exa_all.append(a)
    nk = (g < 0)
    if nk.any():
        exa_nuc.append(m[nk].mean())
    print('  seed %d: 全固相平均取向差 %.2f°，形核晶粒 %d 胞 平均 %.2f°' % (
        seed, a, int(nk.sum()), m[nk].mean() if nk.any() else float('nan')))
print('  汇总: 全体 %.2f°±%.2f, 形核晶粒 %.2f°±%.2f' % (
    np.mean(exa_all), np.std(exa_all), np.mean(exa_nuc), np.std(exa_nuc)))
json.dump(dict(all=exa_all, nuc=exa_nuc), open('/mnt/f/speed_up/bench/exaca/exaca_misorient.json', 'w'), indent=1)