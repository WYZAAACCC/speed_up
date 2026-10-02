#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_goalcheck.py --- 自查：**goal 草案里引用的每个行号**是否与代码一致（P28 纪律）"""
import re

CITES = [
    ('windowB_surface.py', 1085, 'self.phi = np.full((self.nreg'),
    ('windowB_surface.py', 1513, 'def region(self)'),
    ('windowB_surface.py', 1793, 'rng=np.random.default_rng(seed)'),
    ('windowB_surface.py', 1828, None),
    ('windowB_surface.py', 2534, None),
    ('windowB_surface.py', 2573, None),
    ('windowB_surface.py', 2635, None),
    ('windowB_surface.py', 2656, None),
    ('windowB_surface.py', 2789, None),
    ('windowB_surface.py', 2888, None),
    ('windowB_surface.py', 2890, 'self.phi[0] = -np.min'),
    ('windowB_surface.py', 3587, None),
    ('windowB_surface.py', 3845, None),
    ('windowB_surface.py', 3963, None),
    ('windowB_surface.py', 4143, None),
    ('windowB_surface.py', 4510, None),
    ('windowB_surface.py', 5031, None),
    ('windowB_surface.py', 5038, None),
    ('windowB_surface.py', 5193, None),
    ('windowB_surface.py', 5201, None),
    ('windowB_surface.py', 5202, None),
    ('windowB_pf3d.py', 241, 'self.phi = np.zeros((self.nv'),
    ('windowB_pf3d.py', 382, None),
    ('windowB_pf3d.py', 243, None),
    ('_bk_exp.py', 2168, None),
    ('_bk_exp.py', 2389, None),
    ('_bk_exp.py', 2711, None),
    ('_bk_exp.py', 310, None),
]
print('=' * 100)
print('goal 草案引用的行号自查（**没验过的不许写进 goal**）')
print('=' * 100)
bad = 0
for f, n, want in CITES:
    try:
        line = open(f, encoding='utf-8', errors='replace').read().split('\n')[n - 1]
    except Exception as e:
        print('  %-22s:%-6d 读不到（%s）' % (f, n, e))
        bad += 1
        continue
    ok = (want is None) or (want in line)
    if not ok:
        bad += 1
    print('  %s %-22s:%-6d %s' % ('✅' if ok else '❌', f, n, line.strip()[:74]))
print()
print('  ⇒ **%d 处**，其中**不一致 %d 处**' % (len(CITES), bad))
print('=' * 100)
