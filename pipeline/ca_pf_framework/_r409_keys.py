#!/usr/bin/env python3
"""_r409_keys.py —— 打印 seeds/snap 的完整键表 + meta 的几何量（只读）。"""
import json
import os
import sys

import numpy as np

RUN = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mb/dry_saSet2'

for fn in ('seeds.npz', 'snap_00020.npz', 'snap_00400.npz'):
    p = os.path.join(RUN, fn)
    print('=' * 78)
    print('[%s]' % fn)
    if not os.path.exists(p):
        print('  ✗ 不存在')
        continue
    d = np.load(p)
    for k in d.files:
        a = d[k]
        print('  %-16s %-20s %s' % (k, str(a.shape), a.dtype))
    # 变体轴表？
    for k in ('atab', 'npref_tab', 'wtab', 'npref', 'atab_keys'):
        if k in d.files:
            print('  ★ 有轴表：%s' % k)

m = json.load(open(os.path.join(RUN, 'meta.json')))
print('=' * 78)
print('[meta 几何]')
for k in ('N', 'L', 'dx_nm', 'plate', 'gap_nm', 'nv', 'laths', 'vmap',
          'n_hab', 'w_ax', 'a_ax', 'gamma_RS', 'theta_deg', 'omega_mode',
          'omega_max_deg', 'adv', 'Mob', 'DF', 'dt', 't_sim', 'beta_h',
          'beta_w', 'norm_smooth', 'df_const', 'df_start', 'T_end', 'arm'):
    if k in m:
        print('  %-16s = %s' % (k, m[k]))

print('=' * 78)
print('[closure.geometry / params]')
c = json.load(open(os.path.join(RUN, 'closure.json')))
print('  geometry = %s' % json.dumps(c.get('geometry'), ensure_ascii=False))
print('  params   = %s' % json.dumps(c.get('params'), ensure_ascii=False)[:600])
