#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""列出快照 npz 的键/形状/dtype（用于确认 `_r461_sdfhealth.py` 该读哪个键）。"""
import glob
import json
import os
import sys

import numpy as np

for tag in sys.argv[1:] or ['dry_abB', 'dry_abA', 'dry_saSet2']:
    d = os.path.join('_exp/_bk_mb', tag)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    print('=' * 70)
    print('== %s   快照 %d 个' % (tag, len(fs)))
    mj = os.path.join(d, 'meta.json')
    if os.path.exists(mj):
        with open(mj) as fh:
            m = json.load(fh)
        print('   meta 顶层键:', sorted(m.keys())[:30])
        for k in ('dx', 'dx_m', 'dx_nm', 'N', 'nv', 'nreg', 'nreg_used', 'steps'):
            if k in m:
                print('   meta[%s] = %r' % (k, m[k]))
    if not fs:
        continue
    for f in (fs[0], fs[-1]):
        z = np.load(f)
        print('   --', os.path.basename(f))
        for k in z.files:
            a = z[k]
            sh = getattr(a, 'shape', None)
            print('        %-16s %-22s %s' % (k, str(sh), getattr(a, 'dtype', '?')))
