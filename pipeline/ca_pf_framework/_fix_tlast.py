#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fix_tlast.py —— 给 nuc_cfg 加 `t_last_reduce` 参数并写进 self._nuc。"""
import io
import re

P = '/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py'
t = io.open(P, encoding='utf-8').read()

a = '                force_reinit_after_event=None):'
b = '                force_reinit_after_event=None, t_last_reduce=0.0):'
assert t.count(a) == 1, t.count(a)
t = t.replace(a, b)

c = '                         force_reinit_after_event=((not bool(attach))'
d = ('                         t_last_reduce=float(t_last_reduce),\n'
     '                         force_reinit_after_event=((not bool(attach))')
assert t.count(c) == 1, t.count(c)
t = t.replace(c, d)

io.open(P, 'w', encoding='utf-8').write(t)
print('OK')
for i, ln in enumerate(t.split('\n'), 1):
    if 't_last_reduce' in ln:
        print(i, ln.strip()[:100])
