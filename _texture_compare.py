#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_texture_compare.py --- 约定无关的织构/择优对比
对【基底晶粒】(ExaCA 用取向表索引作 GrainID) 直接用取向表算 min_angle(<100>, +Z)，
按胞数加权比较两边的分布：查"存活下来的晶粒是否系统性更对齐"(WC 择优) 以及两码是否一致。
'''
import os, json, glob
import numpy as np
D = '/mnt/f/speed_up/bench/exaca'
RUN = '/root/bench/run'
N = 20
VECS = np.loadtxt(D + '/GrainOrientationVectors.csv', delimiter=',', skiprows=1).reshape(-1, 3, 3)


def min_angle(P):
    '''P 的 3 行 = 3 个 <100> 单位向量；返回与 +Z 的最小夹角(度)'''
    c = np.abs(P[:, 2]) / np.linalg.norm(P, axis=1)
    return float(np.degrees(np.arccos(np.clip(c.max(), 0, 1))))


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


print('取向表: 全部 10000 个取向的 min_angle 分布: 均值 %.2f°, 中位 %.2f°' % (
    np.mean([min_angle(VECS[k]) for k in range(0, 10000, 10)]),
    np.median([min_angle(VECS[k]) for k in range(0, 10000, 10)])))
print()
print('%-28s %-10s %-22s' % ('', '晶粒数', '尺寸加权 min_angle'))
for seed in range(5):
    g = parse_vtk(os.path.join(RUN, 'Exa_seed%d.vtk' % seed), 'GrainID').astype(int)
    ids, cnt = np.unique(g[g > 0], return_counts=True)
    ang = np.array([min_angle(VECS[i - 1]) for i in ids])       # GrainID = 取向表索引
    w = cnt / cnt.sum()
    print('ExaCA   seed %d            %-10d %.2f° (最简单均 %.2f°)' % (
        seed, len(ids), float((ang * w).sum()), ang.mean()))
print()
mine = json.load(open(D + '/mine_stats.json'))
print('我方对比（同一表、同一约定）: 需要在 _mine_mirror 里记录每个基底晶粒的取向索引 -> 见下')