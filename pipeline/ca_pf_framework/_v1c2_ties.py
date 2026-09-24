#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1c2_ties.py --- 正确判据(min Σ)的 40 个双晶算例: 命中/未命中 与 |ΔΣ| 的关系'''
import os, sys, json, glob
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ca3d as C3
import verify_ca3d_wc_cet as W
from scipy import stats
n = W.nhat_tilt(35.0)
rows = []
for f in sorted(glob.glob('_v1_out/t5_wc_pairs__*.json')):
    r = json.load(open(f))
    for c in r['cases']:
        rng = np.random.default_rng(c['seed'] + 1)
        quats = [C3.rand_quat(rng) for _ in range(2)]
        sig = [sum(abs(float(C3.quat_to_axes(q)[:, a] @ n)) for a in range(3)) for q in quats]
        rows.append(dict(seed=c['seed'], sig=sig, d=abs(sig[0]-sig[1]),
                         winner=int(np.argmin(sig)) + 1, onlead=c['onlead']))
rows = [r for r in rows if r['onlead']]
hit = [r for r in rows if r['winner'] in r['onlead']]
mis = [r for r in rows if r['winner'] not in r['onlead']]
print('算例 %d; 命中 %d (%.1f%%), 未命中 %d' % (len(rows), len(hit), 100.0*len(hit)/len(rows), len(mis)))
print()
print('  |ΔΣ| 分布         命中组            未命中组')
for lo, hi in ((0.0, 0.02), (0.02, 0.05), (0.05, 0.10), (0.10, 1.0)):
    h = [r for r in hit if lo <= r['d'] < hi]; m = [r for r in mis if lo <= r['d'] < hi]
    print('  [%.2f, %.2f)       %2d 个            %2d 个' % (lo, hi, len(h), len(m)))
print()
for thr in (0.02, 0.05, 0.10):
    sub = [r for r in rows if r['d'] >= thr]
    k = sum(1 for r in sub if r['winner'] in r['onlead'])
    if sub:
        print('  只看 |ΔΣ| >= %.2f 的 %d 个算例: 命中 %d (%.1f%%), 二项 p = %.3g' % (
            thr, len(sub), k, 100.0*k/len(sub), stats.binomtest(k, len(sub), 0.5).pvalue))
print()
print('  未命中算例明细:')
for r in mis:
    print('     seed %d: Σ = [%.4f, %.4f], ΔΣ = %.4f (胜者 g%d), 实际持有者 %s' % (
        r['seed'], r['sig'][0], r['sig'][1], r['d'], r['winner'], r['onlead']))