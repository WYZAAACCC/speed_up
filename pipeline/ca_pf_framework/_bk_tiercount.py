#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_tiercount.py —— 数一下参数总表里各层各有多少条（用于文档里的数字不手抄）。"""
import collections
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import windowB_closure as CL                                    # noqa: E402

ps = CL.params()
c = collections.Counter(p['tier'] for p in ps)
print('参数总条数 = %d' % len(ps))
for t in ('推', '借', '标', '数'):
    print('  [%s] %d 条' % (t, c.get(t, 0)))
print('  合计 %d' % sum(c.values()))
