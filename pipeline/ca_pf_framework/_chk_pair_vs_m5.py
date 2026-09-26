#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_pair_vs_m5.py --- 判据 D1-b：**界面对富集 vs 配对相容性**是否一致。

物理：若模型真的在按自协调物理选界面，则"界面面积份额高的配对"应当就是
      "rank-1 相容法向弹性能低（ratio 小）的配对" => Spearman rho < 0（负相关）。

用法：python3 _chk_pair_vs_m5.py results_m6route_C_final.npz [更多 npz...]
"""
import json
import sys
import numpy as np
from scipy import stats

tab = json.load(open('_pair_normals_table.json'))['tab']
paths = sys.argv[1:] or ['results_m6route_C_final.npz']
print('=== D1-b: 界面对富集 vs 配对相容性 ===')
for p in paths:
    d = np.load(p)
    reg = d['reg']
    nv = 12
    pair = {}
    for ax in range(3):
        a, b = reg, np.roll(reg, -1, axis=ax)
        sel = (a != b)
        ka, kb = a[sel], b[sel]
        for x, y in zip(ka.ravel(), kb.ravel()):
            if x == 0 or y == 0:
                continue
            kk = '%d-%d' % (min(x, y), max(x, y))
            pair[kk] = pair.get(kk, 0) + 1
    tot = sum(pair.values())
    if tot == 0:
        print('  %s: 无变体-变体界面（f 太小）' % p)
        continue
    keys = [k for k in tab if pair.get(k, 0) > 0]
    share = np.array([pair[k] / tot for k in keys])
    ratio = np.array([tab[k]['ratio'] for k in keys])
    rho, pv = stats.spearmanr(ratio, share)
    print('  %s: 界面总键数 %d，非零配对 %d' % (p, tot, len(keys)))
    print('     Spearman(相容性 ratio, 面积份额) = %+.3f  (p=%.3f)' % (rho, pv))
    top = sorted(keys, key=lambda k: -pair[k])[:5]
    print('     份额 top-5: %s' % ', '.join(
        '%s %.1f%%(ratio=%.1e)' % (k, 100 * pair[k] / tot, tab[k]['ratio']) for k in top))
    strong = sorted(tab, key=lambda k: tab[k]['ratio'])[:6]
    print('     最相容 top-6: %s' % ', '.join(
        '%s(%.1e, 份额%.1f%%)' % (k, tab[k]['ratio'], 100 * pair.get(k, 0) / tot)
        for k in strong))
    verdict = ('PASS(富集在相容对)' if rho < -0.2
               else ('FAIL(无择优/反相关)' if rho > -0.2 else 'NA'))
    print('     => D1-b %s' % verdict)
