#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_perlath.py —— 逐板条的**三轴尺寸**随步数（判"中间板条是长度不长还是厚度不长"）。

用法: python3 _bk_perlath.py <dir> [snap steps...]
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _bk_measure as BM                                        # noqa: E402

d = sys.argv[1]
if not os.path.isabs(d):
    d = os.path.join(HERE, d)
snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
if not snaps:
    print('没有快照:', d)
    raise SystemExit(1)
keys = None
rows = []
for s in snaps:
    z = np.load(s)
    reg = z['region']
    vmap = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
    r = BM.measure_state(reg, float(z['L']) / reg.shape[0], z['n_hab'],
                         z['w_ax'], z['a_ax'], vmap)
    ks = sorted(vmap)
    if keys is None:
        keys = ks
    rows.append((int(z['step']),
                 {k: (r['n_%d' % k], r['w_%d' % k], r['a_%d' % k],
                      r['vol_%d' % k]) for k in ks}))
print('%-28s %s' % (os.path.basename(d), '   '.join('板条%d' % k for k in keys)))
hdr = '  step  ' + '  '.join('%-22s' % ('n/w/a(nm)  V(um3)') for _ in keys)
print(hdr)
for st, dd in rows:
    line = '  %4d  ' % st
    for k in keys:
        n, w, a, v = dd[k]
        line += '%-22s' % ('%3.0f/%3.0f/%4.0f %.4f' % (n * 1e9, w * 1e9, a * 1e9,
                                                       v * 1e18))
    print(line)
print()
print('Δ 相对首快照:')
st0, d0 = rows[0]
stN, dN = rows[-1]
for k in keys:
    n0, w0, a0, v0 = d0[k]
    n1, w1, a1, v1 = dN[k]
    print('  板条%d: Δn=%+6.0f  Δw=%+6.0f  Δa=%+6.0f nm   ΔV=%+5.1f%%'
          % (k, (n1 - n0) * 1e9, (w1 - w0) * 1e9, (a1 - a0) * 1e9,
             100 * (v1 / v0 - 1)))
