#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_growth_exaca.py --- 让 ExaCA 每 100 步输出一帧，追踪各晶粒（尤其形核晶粒）的生长曲线'''
import json, os, subprocess, glob
import numpy as np
BASE = json.load(open('/mnt/f/speed_up/bench/exaca/Inp_SmallDirS_abs.json'))
RUN = '/root/bench/run'
EXA = '/root/bench/ExaCA-master/build/bin/ExaCA'
N = 20
SEEDS = [0, 1]


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


res = {}
for seed in SEEDS:
    d = dict(BASE)
    d['RandomSeed'] = seed
    d['Printing'] = dict(BASE['Printing'], OutputFile='Gr_seed%d' % seed,
                         Intralayer=dict(Increment=100, Fields=['GrainID'], PrintIdleFrames=False))
    p = os.path.join(RUN, 'Inp_gr%d.json' % seed)
    json.dump(d, open(p, 'w'), indent=1)
    for f in glob.glob(os.path.join(RUN, 'Gr_seed%d*.vtk' % seed)):
        os.remove(f)
    r = subprocess.run([EXA, p], cwd=RUN, capture_output=True, text=True)
    frames = sorted(glob.glob(os.path.join(RUN, 'Gr_seed%d*.vtk' % seed)),
                    key=lambda f: int(''.join(c for c in os.path.basename(f).split('.')[0] if c.isdigit())[len(str(seed)):]))
    print('seed %d: 输出 %d 帧 -> %s' % (seed, len(frames),
          [os.path.basename(f) for f in frames[:4]]))
    curve = []
    for f in frames:
        g = parse_vtk(f)
        if len(g) != N ** 3:
            continue
        neg = np.unique(g[g < 0])
        tot = int((g != 0).sum())
        row = dict(n_nuc_cells=int((g < 0).sum()),
                   n_nuc=len(neg),
                   cells={int(k): int((g == k).sum()) for k in neg},
                   tot=tot)
        curve.append(row)
    res[str(seed)] = curve
json.dump(res, open('/mnt/f/speed_up/bench/exaca/exaca_growth.json', 'w'), indent=1)
for seed, curve in res.items():
    print('seed %s 曲线（帧: 形核晶粒数/形核胞数/总固相）: ' % seed +
          ' '.join('%d:%d/%d/%d' % (i, c['n_nuc'], c['n_nuc_cells'], c['tot'])
                   for i, c in enumerate(curve[::max(1, len(curve)//8)])))