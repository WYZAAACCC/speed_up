#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R30 只读审计：汇总 _exp/_bk_closed/*/series.csv 的关键列 + 落盘 meta。"""
import os
import sys
import csv
import glob
import json

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

COLS = ['step', 't_s', 'dt', 'Vt', 'M', 'nreg_used', 'nslab_n', 'nf3_col',
        'runs', 'ncomp_min', 'ncomp_max', 'nf3', 'f3_area_m2', 'f3_area_stair',
        'f3_pos_m', 'f3_pos_dx', 'f3_std_m', 'n_lath', 'w_lath', 'a_lath',
        'box_touch', 'finite', 'psi_mean', 'cfl_used']


def rows_of(path):
    # AGENTS §3.6：/mnt/f 9p 缓存会静默返回过期数据 ⇒ 读到与 wc -l 一致为止
    for _ in range(5):
        with open(path, 'r') as f:
            rs = list(csv.DictReader(f))
        with open(path, 'rb') as f:
            n = sum(1 for _ in f) - 1
        if len(rs) == n:
            return rs
    return rs


def main():
    pats = sys.argv[1:] or ['_exp/_bk_closed/*/series.csv']
    for pat in pats:
        for p in sorted(glob.glob(pat)):
            rs = rows_of(p)
            if not rs:
                print('%-46s (空)' % p)
                continue
            meta = os.path.join(os.path.dirname(p), 'meta.json')
            arm = tag = '?'
            if os.path.exists(meta):
                m = json.load(open(meta))
                arm = m.get('arm'); tag = m.get('tag')
                g0 = m.get('gamma0')
            else:
                g0 = None
            print('=' * 110)
            print('%s   arm=%s tag=%s  γ0=%s  rows=%d' % (p, arm, tag, g0, len(rs)))
            hdr = ['step', 'Vt_um3', 'nslab', 'nf3col', 'runs', 'nf3',
                   'f3pos_dx', 'f3std_nm', 'a_lath_nm', 'box', 'psi', 'cfl']
            print('  ' + ' | '.join('%-9s' % h for h in hdr))
            for r in rs:
                def g(c):
                    v = r.get(c, '')
                    return v if v not in (None, '') else 'nan'
                def f(c, sc=1.0, fmt='%.4g'):
                    try:
                        return fmt % (float(r[c]) * sc)
                    except Exception:
                        return 'nan'
                out = [r['step'],
                       f('Vt', 1e18, '%.4f'),
                       r.get('nslab_n', ''),
                       r.get('nf3_col', ''),
                       r.get('runs', ''),
                       g('nf3'),
                       f('f3_pos_dx', 1.0, '%+.3f'),
                       f('f3_std_m', 1e9, '%.1f'),
                       f('a_lath', 1e9, '%.0f'),
                       g('box_touch'),
                       f('psi_mean', 1.0, '%.4f'),
                       f('cfl_used', 1.0, '%.3f')]
                print('  ' + ' | '.join('%-9s' % o for o in out))


if __name__ == '__main__':
    main()
