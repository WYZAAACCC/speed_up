#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30-AUDIT：`seeds.npz`（t=0 全量状态）清了什么？逐个算例列 key/shape。"""
import glob
import json
import os
import sys

import numpy as np

root = sys.argv[1] if len(sys.argv) > 1 else \
    '/mnt/f/speed_up/pipeline/ca_pf_framework/_exp'
pat = os.path.join(root, '*', 'seeds.npz')
pat2 = os.path.join(root, '*', '*', 'seeds.npz')
seen = set()
rows = []
for p in sorted(glob.glob(pat) + glob.glob(pat2)):
    if p in seen:
        continue
    seen.add(p)
    try:
        z = np.load(p, allow_pickle=False)
    except Exception as e:                                       # noqa: BLE001
        print('ERR %s %s' % (p, e))
        continue
    ks = []
    for k in z.files:
        a = z[k]
        ks.append('%s%s:%s' % (k, list(a.shape), a.dtype))
    rows.append((os.path.getsize(p), p, ks))
    z.close()
rows.sort(reverse=True)
print('共 %d 个 seeds.npz' % len(rows))
for sz, p, ks in rows[:14]:
    print('%10.1f MB  %s' % (sz / 1e6,
                             p.replace('/mnt/f/speed_up/pipeline/'
                                       'ca_pf_framework/_exp/', '')))
    print('            %s' % '  '.join(ks))
print()
print('=== 最小/最典型的几个 ===')
for sz, p, ks in rows[-4:]:
    print('%10.1f MB  %s' % (sz / 1e6,
                             p.replace('/mnt/f/speed_up/pipeline/'
                                       'ca_pf_framework/_exp/', '')))
    print('            %s' % '  '.join(ks))
