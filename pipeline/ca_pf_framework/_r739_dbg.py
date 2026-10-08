#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r739_dbg.py <root> <tag> ... —— 读 `nuc_dbg.json`，**验证开关是否真的生效**（`P43`）。

⚠ `R725` 的教训：我第一版因为 `--nuc-init 0` 把 `fresh` 通道关了，
   于是"无效应"是**必然**，不是发现。
⇒ 本脚本先问：**`stack` 通道跑了吗？`dg_pick` 计数器动了吗？**
"""
import json
import os
import sys

root = sys.argv[1]
for t in sys.argv[2:]:
    p = os.path.join(root, 'dry_%s' % t, 'nuc_dbg.json')
    print('=' * 90)
    print('%s  →  %s' % (t, p))
    print('=' * 90)
    if not os.path.isfile(p):
        print('  ⚠ 无 nuc_dbg.json')
        continue
    with open(p) as f:
        d = json.load(f)
    print('  n_eng_ev        = %s' % d.get('n_eng_ev'))
    print('  n_events_by_mode= %s' % d.get('n_events_by_mode'))
    dbg = d.get('dbg') or {}
    for k in sorted(dbg):
        print('    dbg.%-14s = %s' % (k, dbg[k]))
    cfg = d.get('nuc_cfg') or {}
    for k in ('R', 't', 'seed', 'n_fresh', 'n_stack', 'stack_pick_dg'):
        if k in cfg:
            print('  nuc_cfg.%-12s = %s' % (k, cfg[k]))
