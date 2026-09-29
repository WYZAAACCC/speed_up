#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30：查 meta.json 里到底记了哪些"薄膜/ψ 参数"与哪些开关。"""
import os
import json

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

for p in ('_exp/_bk_ctrl/auto_ctrl/meta.json', '_exp/_bk_closed/dry_cln11/meta.json'):
    m = json.load(open(p))
    print('=' * 90)
    print(p)
    print(' 顶层键 :', sorted(m.keys()))
    ea = m.get('exp_args', {})
    print(' exp_args 键数 :', len(ea))
    hit = {k: v for k, v in ea.items() if 'film' in k or 'psi' in k or 'phi' in k}
    print(' 与 film/psi/phi 相关的键 :', hit or '（无）')
    hit2 = {k: v for k, v in m.items() if 'film' in k or 'psi' in k}
    print(' 顶层 film/psi 键 :', hit2 or '（无）')
