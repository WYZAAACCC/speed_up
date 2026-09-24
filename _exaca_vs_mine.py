#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_exaca_vs_mine.py --- 同一初始条件（ExaCA Inp_SmallDirSolidification）下两码对比
ExaCA 侧: 改 RandomSeed 跑多次 -> 解析 VTK -> 统计
我方:    完全照抄其约定（G/R/dx/dt/底面 25% 位点/形核谱 dtn=5,dtsigma=0.5,n_max=250e12）
'''
import json, os, subprocess, sys, glob
import numpy as np
EXA = '/root/bench/ExaCA-master/build/bin/ExaCA'
RUN = '/root/bench/run'
BASE = json.load(open('/mnt/f/speed_up/bench/exaca/Inp_SmallDirS_abs.json'))
SEEDS = [0, 1, 2, 3, 4]


def run_exaca(seed):
    d = dict(BASE)
    d['RandomSeed'] = seed
    d['Printing'] = dict(BASE['Printing'], OutputFile='Exa_seed%d' % seed)
    p = os.path.join(RUN, 'Inp_seed%d.json' % seed)
    json.dump(d, open(p, 'w'), indent=1)
    r = subprocess.run([EXA, p], cwd=RUN, capture_output=True, text=True)
    out = os.path.join(RUN, 'Exa_seed%d.vtk' % seed)
    if not os.path.exists(out):
        print('  !! seed%d 失败: %s' % (seed, r.stderr[-300:]))
        return None
    return out


def parse_vtk(fp, field='GrainID'):
    with open(fp) as f:
        lines = f.readlines()
    # 找 SCALARS <field> ... 之后到 LOOKUP_TABLE 的数据行
    i = 0
    while i < len(lines):
        if lines[i].strip().upper().startswith('SCALARS') and field.lower() in lines[i].lower():
            j = i + 2
            vals = []
            while j < len(lines):
                t = lines[j].strip()
                if not t or t[0].isalpha():
                    break
                vals += [int(float(x)) for x in t.split()]
                j += 1
            return np.array(vals)
        i += 1
    raise RuntimeError('未找到字段 ' + field)


def stats_from_gid(gid, nuke):
    '''nuke: 布尔数组，标记哪些 gid 是"形核"晶粒'''
    tot = len(gid)
    ids, cnt = np.unique(gid, return_counts=True)
    is_nuke = np.array([nuke(int(g)) for g in ids])
    return dict(n_grain=len(ids), frac_nuke=float(cnt[is_nuke].sum())/tot,
                mean_size=float(cnt.mean()), max_size=int(cnt.max()),
                mean_size_nuke=float(cnt[is_nuke].mean()) if is_nuke.any() else 0.0,
                n_nuke=int(is_nuke.sum()))


print('=' * 96)
print('A) ExaCA 多次运行（同输入文件，只改 RandomSeed）')
print('=' * 96)
exa = []
for s in SEEDS:
    fp = run_exaca(s)
    if fp is None:
        continue
    gid = parse_vtk(fp)
    st = stats_from_gid(gid, lambda g: g < 0)          # ExaCA: 形核晶粒用负 ID
    st['seed'] = s
    exa.append(st)
    print('  seed %d: 晶粒数 %3d, 形核晶粒 %2d 个, 形核占比 %.3f, 平均晶粒 %6.1f 胞' % (
        s, st['n_grain'], st['n_nuke'], st['frac_nuke'], st['mean_size']))
if exa:
    print('  ------ ExaCA 汇总: 晶粒数 %.1f±%.1f, 形核占比 %.3f±%.3f, 平均晶粒 %.1f±%.1f 胞' % (
        np.mean([e['n_grain'] for e in exa]), np.std([e['n_grain'] for e in exa]),
        np.mean([e['frac_nuke'] for e in exa]), np.std([e['frac_nuke'] for e in exa]),
        np.mean([e['mean_size'] for e in exa]), np.std([e['mean_size'] for e in exa])))
json.dump(exa, open('/mnt/f/speed_up/bench/exaca/exaca_stats.json', 'w'), indent=1)