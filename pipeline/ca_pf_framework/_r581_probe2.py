#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_probe2.py --- 探针：`seeds.npz` / `snap_*.npz` / `meta.json` 里到底有什么键。

为什么先探针：C1（随机形核的**均匀性检验**）需要位点坐标，C2/C6（几何 / 取向）
需要快照。**不能假设它们的键名**——本仓已多次因"猜键名/猜格式"白跑。
"""
import json
import os
import sys

import numpy as np

R = '_exp/_bk_p2'
tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
d = os.path.join(R, 'dry_' + tag)


def dump_npz(p):
    if not os.path.exists(p):
        print('  （缺 %s）' % p); return
    z = np.load(p, allow_pickle=True)
    print('  %s : %d 个键，%.2f MB' % (os.path.basename(p),
                                      len(z.files), os.path.getsize(p) / 2 ** 20))
    for k in z.files:
        v = z[k]
        try:
            if isinstance(v, np.ndarray):
                print('    %-26s shape=%-18s dtype=%-10s %s'
                      % (k, str(v.shape), v.dtype,
                         ('示例 %s' % np.array2string(v.reshape(-1)[:4], precision=4))
                         if v.size else '（空）'))
            else:
                print('    %-26s %r' % (k, type(v)))
        except Exception as e:
            print('    %-26s ⚠ %r' % (k, e))


print('=' * 88)
print('探针 tag=%s' % tag)
print('=' * 88)
mp = os.path.join(d, 'meta.json')
if os.path.exists(mp):
    m = json.load(open(mp))
    print('meta.json 顶层键（%d）：' % len(m))
    for k in list(m.keys())[:40]:
        v = m[k]
        s = ('dict(%d)' % len(v)) if isinstance(v, dict) else \
            ('list(%d)' % len(v)) if isinstance(v, list) else repr(v)[:60]
        print('  %-24s %s' % (k, s))
    ea = m.get('exp_args', {})
    if isinstance(ea, dict):
        print('  exp_args 里的关键项：')
        for k in ('plate_L', 'plate_W', 'plate_T', 'gamma0', 'beta_h',
                  'nuc_overlap_nm', 'nuc_periodic_seed', 'nuc_block_target',
                  'nuc_fresh_every', 'laths', 'N', 'dx_nm', 'seed',
                  'nuc_law', 'alpha_km', 'T_end', 'cool_rate'):
            if k in ea:
                v = ea[k]
                print('    %-22s %s' % (k, str(v)[:70]))
print()
for f in ('seeds.npz', 'snap_00000.npz', 'snap_00200.npz', 'snap_00400.npz'):
    dump_npz(os.path.join(d, f))
