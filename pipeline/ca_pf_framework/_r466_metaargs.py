#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看 meta.json 的 `exp_args` 里到底有没有 `alpha_km` / `cool_rate` / `T_start`。
R465 发现 abB 给出 99.9% 而 abA 给出 46.4% —— 两者冷速相同 ⇒ 必有一处读错。
本脚本把原始键值打出来定位。"""
import json
import os
import sys

for tag in (sys.argv[1:] or ['dry_abA', 'dry_abB', 'dry_r464A']):
    p = os.path.join('_exp/_bk_mb', tag, 'meta.json')
    if not os.path.exists(p):
        print('✗ 没有 %s' % p)
        continue
    with open(p) as fh:
        m = json.load(fh)
    print('=' * 70)
    print('== %s' % tag)
    ea = m.get('exp_args')
    print('   exp_args 类型=%s 键数=%s' % (type(ea).__name__,
                                          len(ea) if hasattr(ea, '__len__') else '?'))
    if isinstance(ea, dict):
        for k in ('alpha_km', 'cool_rate', 'cool_ratio', 'T_start', 'T_end',
                  'nuc_law', 'steps', 'reinit_dt', 'beta_h', 'gamma0', 'N', 'dx_nm'):
            print('     exp_args[%-12s] = %r' % (k, ea.get(k, '**缺失**')))
    for k in ('df_start', 'dt', 'Mob', 'N', 'dx_nm'):
        print('     meta[%-16s] = %r' % (k, m.get(k, '**缺失**')))
