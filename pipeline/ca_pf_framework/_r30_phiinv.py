#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：列出**所有存了 `phi` 的快照**的 N / nv / 未压缩大小 / 实际大小。"""
import glob
import os
import sys

import numpy as np

pat = sys.argv[1] if len(sys.argv) > 1 else \
    '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/*/*/snap_*.npz'
print('%-52s %5s %5s %5s %10s %10s' % ('file', 'Nkey', 'regN', 'nv',
                                       'rawMB', 'diskMB'))
for p in sorted(glob.glob(pat)):
    try:
        z = np.load(p, allow_pickle=False)
    except Exception:                                           # noqa: BLE001
        continue
    if 'phi' not in z.files:
        z.close()
        continue
    ph = z['phi']
    reg = z['region']
    nk = int(z['N']) if 'N' in z.files else -1
    print('%-52s %5d %5d %5d %10.1f %10.2f'
          % (p.replace('/mnt/f/speed_up/pipeline/ca_pf_framework/', ''),
             nk, reg.shape[0], ph.shape[0], ph.nbytes / 1e6,
             os.path.getsize(p) / 1e6))
    z.close()
