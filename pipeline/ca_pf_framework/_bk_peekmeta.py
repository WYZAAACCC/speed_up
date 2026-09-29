#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_peekmeta.py —— 打印若干算例 `meta.json` 里**决定它到底是什么**的那些字段。

为什么单独一个文件：PowerShell → wsl → python -c 的引号会被吃三层
（本仓库已多次踩坑）⇒ 一律写成文件再调。
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = ('arm', 'steps', 'nv', 'laths', 'grow_stack', 'nuc_every', 'plate',
        'beta_h', 'beta_w', 'norm_smooth', 'reinit_dt', 'dx_nm', 'N')


def main(argv):
    paths = argv[1:] or ['_exp/_bk_ctrl/gpos_L200']
    for p in paths:
        mp = os.path.join(_HERE, p, 'meta.json')
        if not os.path.exists(mp):
            print('%-40s （无 meta.json）' % p)
            continue
        d = json.load(open(mp, encoding='utf-8'))
        print('--- %s' % p)
        for k in KEYS:
            if k in d:
                print('    %-14s %s' % (k, d[k]))
        ea = d.get('exp_args') or {}
        for k in ('gamma0', 'nuc_law', 'eng_cadence', 'alpha_km', 'cool_ratio',
                  'T_end', 'eng_t_nm', 'eng_r_nm', 'eng_elong'):
            if k in ea:
                print('    arg:%-11s %s' % (k, ea[k]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
