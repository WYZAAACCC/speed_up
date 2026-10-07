#!/usr/bin/env python3
"""_r408_probe.py —— 快照/meta 格式探针（只读，不改任何东西）。

目的：在动 `facet_project` 之前，先把**载荷**看清楚：
  * 快照里有什么键、什么形状；
  * `meta.json` 里 `exp_args` 的关键参数（N / dx / laths / multi_block /
    facet_proj / nuc_* / arm / grow_stack …）；
  * 变体表 `atab` / `npref_tab` / `wtab` 是否在快照里（面片投影要用它们）。

⚠ 纪律：本脚本**只读**，不做任何判读；判读在 `_r409`。
"""
import json
import os
import sys

import numpy as np

RUN = sys.argv[1] if len(sys.argv) > 1 else \
    '_exp/_bk_mb/dry_saSet2'
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 20

print('=' * 78)
print('_r408 探针：%s @ step %d' % (RUN, STEP))
print('=' * 78)

snap = os.path.join(RUN, 'snap_%05d.npz' % STEP)
print('\n[1] 快照 %s' % snap)
if os.path.exists(snap):
    d = np.load(snap)
    for k in d.files:
        a = d[k]
        print('    %-16s %-18s %s' % (k, str(a.shape), a.dtype))
else:
    print('    ✗ 不存在')

print('\n[2] meta.json')
mp = os.path.join(RUN, 'meta.json')
if os.path.exists(mp):
    m = json.load(open(mp))
    print('    顶层键：%s' % sorted(m.keys()))
    ea = m.get('exp_args', m.get('args', {}))
    print('    exp_args 键数：%d' % len(ea))
    WANT = ('N', 'dx_nm', 'laths', 'multi_block', 'block_gap_nm', 'facet_proj',
            'nuc_law', 'nuc_init', 'nuc_every', 'grow_stack', 'arm',
            'nuc_mode', 'var_rule', 'steps', 'every', 'snap_every',
            'plate_L', 'plate_W', 'plate_T', 'gamma0', 'omega_mode',
            'omega_max_deg', 'pair_aniso', 'nuc_overlap_nm', 'eng_cadence',
            'alpha_km', 'T_end', 'seed')
    print('    ---- 关心的参数 ----')
    for k in WANT:
        if k in ea:
            print('      %-18s = %s' % (k, ea[k]))
    miss = [k for k in WANT if k not in ea]
    if miss:
        print('    （meta 里没有：%s）' % ', '.join(miss))
else:
    print('    ✗ 不存在')

print('\n[3] seeds.npz')
sp = os.path.join(RUN, 'seeds.npz')
if os.path.exists(sp):
    d = np.load(sp)
    for k in d.files:
        a = d[k]
        print('    %-16s %-18s %s' % (k, str(a.shape), a.dtype))
else:
    print('    ✗ 不存在')

print('\n[4] closure.json 顶层')
cp = os.path.join(RUN, 'closure.json')
if os.path.exists(cp):
    c = json.load(open(cp))
    print('    %s' % sorted(c.keys()))
else:
    print('    ✗ 不存在')
print('=' * 78)
