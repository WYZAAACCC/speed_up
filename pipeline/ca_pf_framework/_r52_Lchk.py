#!/usr/bin/env python3
"""R52: 快照里的 `L` 到底是几？—— 它是**离线重算的唯一尺度来源**（`dx = L/N`）。
若 `L = 0`，则所有离线几何量（含 `_r47_rates.py` 的面间距）**全被算成 0**。
"""
import glob
import os

import numpy as np

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
arms = ['_exp/_bk_closed/dry_cln11', '_exp/_bk_mb/dry_mb1s',
        '_exp/_bk_mb/dry_mb1s62', '_exp/_bk_mb/dry_b62r',
        '_exp/_bk_mb/dry_r49cad', '_exp/_bk_eng/dry_r30reg',
        '_exp/_bk_mb/dry_mb1L', '_exp/_bk_mb/dry_r49vb']
print('  %-24s %-8s %-14s %-10s %s' % ('臂', '快照数', 'L (m)', 'N', 'dx = L/N (nm)'))
for d in arms:
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        print('  %-24s （无快照）' % os.path.basename(d))
        continue
    z = np.load(snaps[0])
    L = float(z['L']) if 'L' in z.files else float('nan')
    N = int(z['N']) if 'N' in z.files else 0
    print('  %-24s %-8d %-14.6e %-10d %s'
          % (os.path.basename(d), len(snaps), L, N,
             ('%.3f' % (L / N * 1e9)) if N else '?'))
print()
print('★ 若某臂 L=0 ⇒ 该臂的快照**不能**做任何按长度标定的离线重算；')
print('  `_r47_rates.py` 用的正是 `dx = z[\'L\']/N` ⇒ 会把它整条臂算成 0。')
