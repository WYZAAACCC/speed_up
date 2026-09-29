#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_snapchk.py —— 检查快照内容是否满足"量具可事后重测"（用户明确要求）。"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
pat = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_t3/*/snap_*.npz'
fs = sorted(glob.glob(os.path.join(HERE, pat)))
if not fs:
    print('没有匹配的快照：', pat)
    raise SystemExit(1)
for f in fs:
    z = np.load(f)
    need = ('region', 'n_hab', 'w_ax', 'a_ax', 'N', 'L', 'vmap_keys', 'vmap_vals')
    miss = [k for k in need if k not in z.files]
    print('%-46s %7.2f MB  keys=%s  %s'
          % (os.path.relpath(f, HERE), os.path.getsize(f) / 1e6,
             ','.join(z.files), ('缺 ' + str(miss)) if miss else 'OK(量具所需齐全)'))
    print('    region: %s %s   phi: %s'
          % (z['region'].dtype, z['region'].shape,
             ('%s %s' % (z['phi'].dtype, z['phi'].shape))
             if 'phi' in z.files else '未存'))
