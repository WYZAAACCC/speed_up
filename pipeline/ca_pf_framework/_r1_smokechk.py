#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_smokechk.py --- 冒烟算例的 CSV 记账列检查（`step`/`t_s`/`dG_max`/reinit）。"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
d = sys.argv[1] if len(sys.argv) > 1 else '_csvfix_smoke'
p = os.path.join(HERE, '_exp', d, 'series.csv')
if not os.path.exists(p):
    print('✗ 没有 %s' % p); sys.exit(1)
rows = list(csv.DictReader(open(p)))
print('rows = %d' % len(rows))
print('%-6s %-12s %-12s %-12s %-8s %-8s %s'
      % ('step', 't_s', 'dt', 'dG_max', 'nreinit', 'adv_wall', 'ncomp'))
for r in rows:
    print('%-6s %-12s %-12s %-12s %-8s %-8s %s'
          % (r.get('step'), r.get('t_s'), r.get('dt'), r.get('dG_max'),
             r.get('nreinit'), r.get('adv_wall'), r.get('ncomp')))
B = ['step', 't_s', 'dt', 'dG_max', 'nreinit', 'nskip', 'regflip', 'adv_wall',
     'reinit_wall', 'reinit_pairs']
M = ['L_cal', 'W_cal', 'T_cal', 'ncell', 'LW_cal', 'fill_cal', 'ncomp', 'ok']
# ★ 逐分量（多核）量具：确认"只在显著分量上取中位"的修复生效
C = ['ncomp', 'nsig', 'ncomp_used', 'align_deg', 'align_deg_big', 'Lc', 'Wc', 'Tc']
print()
for k in B + M:
    vals = [r.get(k) for r in rows]
    nempty = sum(1 for v in vals if v in (None, ''))
    print('%-12s 空 %d/%d  -> %s' % (k, nempty, len(vals), vals))
print('\n--- 逐分量量具（多核）---')
for k in C:
    vals = [r.get(k, '（无此列）') for r in rows]
    print('%-14s -> %s' % (k, vals))
print('\n`fill_cal` 是否真的进了表头：%s'
      % ('✅ 是' if 'fill_cal' in rows[0] else '⛔ 否'))
nb = sum(1 for r in rows for k in B if r.get(k) in (None, ''))
nm = sum(1 for r in rows for k in M if r.get(k) in (None, ''))
print('\n记账列空值 %d 个；测量列空值 %d 个' % (nb, nm))
print('（`step=0` 那一行的 `dG_max`/`adv_wall` 为空是**正常**的：'
      '步进还没算过，`advance` 未产生 `dG_max`）')
print('⇒ %s' % ('✅ 修复在真实算例上生效' if nb <= len(B) and nm == 0
                else '⚠ 需逐列看上面的清单'))
mp = os.path.join(HERE, '_exp', d, 'meta.json')
if os.path.exists(mp):
    m = json.load(open(mp))
    print('meta.every = %s ；meta.steps = %s ；sha256 = %s'
          % (m.get('every'), m.get('steps'),
             list((m.get('sha256') or {}).values())[:1]))
