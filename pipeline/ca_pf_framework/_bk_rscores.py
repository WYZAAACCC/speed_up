#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_rscores.py —— R-1..R-5：引擎形核在**不同随机种子**下的稳健性。

用法: python3 _bk_rscores.py eng12 eng13 eng14
"""
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM                                        # noqa: E402
import _bk_cmp as CMP                                           # noqa: E402

TAGS = sys.argv[1:] or ['eng12', 'eng13', 'eng14']
res = {}
for tag in TAGS:
    d = os.path.join(HERE, '_exp/_bk_eng/eng_%s' % tag)
    rows = list(csv.DictReader(open(os.path.join(d, 'series.csv'))))
    snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')])
    z = np.load(os.path.join(d, snaps[-1]))
    reg = z['region']
    dx = float(z['L']) / reg.shape[0]
    nh = np.asarray(z['n_hab'], float)
    vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    r = BM.measure_state(reg, dx, nh, z['w_ax'], z['a_ax'], vmap)
    cv = BM.snapshot_coverage(z)
    present = [k for k in sorted(vmap) if r['vol_%d' % k] > 0]
    th = {k: CMP.robust_thickness(reg, dx, nh, k) * 1e9 for k in present}
    nf = os.path.join(d, 'nuc_dbg.json')
    dbg = json.load(open(nf, encoding='utf-8'))['dbg'] if os.path.exists(nf) else {}
    # 逐对（末态）
    pairs = {}
    for ii, i in enumerate(present):
        for j in present[ii + 1:]:
            if vmap[i] != vmap[j]:
                continue
            A = BM._area_from_faces(BM._faces_between(reg == i, reg == j), nh, dx)
            if A > 1e-4 * 1e-12:
                pairs[(i, j)] = A * 1e12
    res[tag] = dict(rows=rows, r=r, cv=cv, th=th, dbg=dbg, pairs=pairs,
                    runs=rows[-1]['runs'], present=present)

print('=' * 104)
for tag in TAGS:
    R = res[tag]
    print('臂 %s   runs=%s   末态 nslab=%s' % (tag, R['runs'], R['rows'][-1]['nslab_n']))
    print('   R-1 nslab 末值=6 且 runs 无重复        : %s'
          % ('PASS' if (int(R['rows'][-1]['nslab_n']) == 6
                        and len(set(R['runs'].split('/'))) == 6) else '**FAIL**'))
    bm = max(R['cv']['beta_frac'].values()) if R['cv']['beta_frac'] else 0.0
    print('   R-2 V-7b 最差对=%.3f（≤0.25 且各对 ≤0.20）: %s'
          % (bm, 'PASS' if bm <= 0.20 else ('部分' if bm <= 0.25 else '**FAIL**')))
    jj = []
    ns = [int(x['nslab_n']) for x in R['rows']]
    for i in range(1, len(R['rows'])):
        if ns[i] != ns[i - 1]:
            continue
        a0 = float(R['rows'][i - 1]['f3_pos_dx'] or 'nan')
        a1 = float(R['rows'][i]['f3_pos_dx'] or 'nan')
        if np.isfinite(a0) and np.isfinite(a1):
            jj.append(abs(a1 - a0))
    v3g = max(jj) if jj else float('nan')
    print('   R-3 V-3g=%.4f Δx（≤0.12）            : %s'
          % (v3g, 'PASS' if v3g <= 0.12 else '**FAIL**'))
    ap = max(R['pairs'].values()) if R['pairs'] else 0.0
    print('   R-4 逐对面积 max=%.3f µm²（≤1.8）；接触对=%d 对 %s'
          % (ap, len(R['pairs']),
             'PASS' if ap <= 1.8 else '**FAIL**'))
    print('       接触对: %s' % '  '.join('%d-%d=%.2f' % (a, b, v)
                                          for (a, b), v in sorted(R['pairs'].items())))
    nc = max(int(x['ncomp_max']) for x in R['rows'])
    ncb = max(int(x['ncompbig_max']) for x in R['rows'])
    print('   R-5 ncomp_max 全程 max=%d（原始口径）；ncompbig_max max=%d（**显著口径**）'
          % (nc, ncb))
    print('       厚度(剔孤儿)=%s nm；Vt=%.4f µm³；forced_reinit=%s；nfsv_nofield=%s'
          % ('/'.join('%.0f' % R['th'][k] for k in R['present']),
             float(R['rows'][-1]['Vt']) * 1e18, R['dbg'].get('forced_reinit'),
             R['dbg'].get('nfsv_nofield')))
    print('-' * 104)
