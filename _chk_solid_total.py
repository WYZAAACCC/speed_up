#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_chk_solid_total.py --- 从 ExaCA 输出 VTK 直接数"全固相"（GrainID != 0）'''
import os, glob
import numpy as np
RUN = '/root/bench/run'
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
    raise RuntimeError('no field ' + fp)

tot = []
for seed in range(20):
    fp = os.path.join(RUN, 'Ti_seed%d.vtk' % seed)
    if not os.path.exists(fp):
        continue
    g = parse_vtk(fp)
    solid = int((g != 0).sum()); neg = int((g < 0).sum())
    tot.append(solid)
print('ExaCA 20 种子：固相胞数(含 Active，即 GrainID!=0) 均值 = %.1f，范围 %d..%d（域 = 8000）' % (
    np.mean(tot), min(tot), max(tot)))
print('我方 = 8000（全固）  ⇒ 相对差 %+.1f%%' % (100*(8000 - np.mean(tot))/np.mean(tot)))