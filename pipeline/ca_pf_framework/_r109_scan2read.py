#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r109_scan2read.py —— 读 R104/R107 的 PAIR 几何扫描（统一判据 `nf2(t=0) == 0`）。"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
TAGS = ['pg900', 'pg1000', 'pg1100',
        'q600g1000', 'q600g1200', 'q600g1400', 'q450g1200']


def main():
    print('=' * 100)
    print('_r109 —— PAIR 集几何扫描汇总（判据：`nf2(t=0) == 0`）')
    print('=' * 100)
    print('  %-11s %-5s %-8s %-7s %-7s %-10s %-9s %s'
          % ('tag', 'N', 'L', 'W', 'gap', 'nf2(t=0)', 'nblk_sig', '判定'))
    ok, errs = [], []
    for t in TAGS:
        d = os.path.join(MB, 'dry_' + t)
        p = os.path.join(d, 'series.csv')
        mj = os.path.join(d, 'meta.json')
        L = None
        for pre in ('_w2_r104_%s.log' % t, '_w2_r107_%s.log' % t):
            q = os.path.join(HERE, pre)
            if os.path.exists(q):
                L = q
                break
        if not os.path.exists(p):
            e = ''
            if L:
                for line in open(L, encoding='utf-8', errors='replace'):
                    if 'exceeds domain' in line or 'ValueError' in line:
                        e = line.strip()[:70]
                        break
            errs.append((t, e or '（无 series.csv）'))
            print('  %-11s %-5s %-8s %-7s %-7s %-10s %-9s %s'
                  % (t, '-', '-', '-', '-', '**崩**', '-', '❌ ' + (e or '无产物')))
            continue
        rows = list(csv.DictReader(open(p)))
        meta = json.load(open(mj)) if os.path.exists(mj) else {}
        ea = meta.get('exp_args', {}) or {}
        try:
            nf2 = int(float(rows[0].get('nf2')))
        except (TypeError, ValueError):
            nf2 = -1
        good = nf2 == 0
        if good:
            ok.append((t, ea.get('plate_L'), ea.get('plate_W'),
                       ea.get('block_gap_nm')))
        print('  %-11s %-5s %-8s %-7s %-7s %-10s %-9s %s'
              % (t, meta.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                 ea.get('block_gap_nm'), nf2, rows[0].get('nblk_sig'),
                 '✅ **分离**' if good else '❌ 已接触'))
    print()
    if ok:
        print('  ⇒ **PAIR 集可用构型：%s**' % (ok,))
    else:
        print('  ⇒ ⚠ PAIR 集（`{1..6}`）在这些档上**都没有**分离 ⇒'
              ' 改用 `_r108` 挑出的候选集 `{1,2,3,4,7,8}`（`r_min` 同为 0.4828，'
              '但**直线度 0.013** 而不是 0.276）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
