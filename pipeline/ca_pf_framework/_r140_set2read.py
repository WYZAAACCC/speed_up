#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r140_set2read.py —— R137（集2 `{1,2,3,4,7,8}`）的几何测试判读。

判据 `nf2(t=0) == 0`。集2 的 `r_min` 与 `{1..6}` **同为 0.4828**（不可自协调），
但布局轴直线度 **0.013**（vs 0.276）⇒ 好放得多。
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
TAGS = ['s2a', 's2b', 's2c', 's2d', 's2e', 's2f']
# 对照：ODD 集在同一几何上的读数（来自 `_r102`/`_r121`）
ODD_REF = {'sgG': 'N=112 L=1000 W=500 T=510 gap=1300',
           't1N112L800': 'N=112 L=800 W=600 T=635 gap=1200',
           't3N128L1000': 'N=128 L=1000 W=600 T=635 gap=1300'}


def main():
    print('=' * 100)
    print('_r140 —— 集2 `{1,2,3,4,7,8}` 的几何测试（判据 `nf2(t=0)==0`）')
    print('=' * 100)
    print('  %-5s %-5s %-7s %-6s %-6s %-7s %-10s %-7s %s'
          % ('tag', 'N', 'L', 'W', 'T', 'gap', 'nf2(t=0)', 'nblk', '判定'))
    ok = []
    for t in TAGS:
        d = os.path.join(MB, 'dry_' + t)
        p = os.path.join(d, 'series.csv')
        mj = os.path.join(d, 'meta.json')
        if not os.path.exists(p):
            e = ''
            L = os.path.join(HERE, '_w2_r137_%s.log' % t)
            if os.path.exists(L):
                for line in open(L, encoding='utf-8', errors='replace'):
                    if 'exceeds domain' in line:
                        e = '崩：种子超域'
                        break
            print('  %-5s %s' % (t, e or '（未跑）'))
            continue
        rows = list(csv.DictReader(open(p)))
        meta = json.load(open(mj)) if os.path.exists(mj) else {}
        ea = meta.get('exp_args', {}) or {}
        nf2 = rows[0].get('nf2')
        good = str(nf2) == '0'
        if good:
            ok.append((t, ea.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                       ea.get('plate_T'), ea.get('block_gap_nm')))
        print('  %-5s %-5s %-7s %-6s %-6s %-7s %-10s %-7s %s'
              % (t, ea.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                 ea.get('plate_T'), ea.get('block_gap_nm'), nf2,
                 rows[0].get('nblk_sig'),
                 '✅ **分离**' if good else '❌ 重叠'))
    print()
    print('  ---- ODD 集在同一几何上的对照（`_r102`/`_r121`）----')
    for k, v in ODD_REF.items():
        print('     %-14s %s  ⇒ `nf2(0)=0` ✅' % (k, v))
    print()
    if ok:
        print('  ⇒ **集2 可用几何（%d 个）**：' % len(ok))
        for x in ok:
            print('     %-5s N=%s L=%s W=%s T=%s gap=%s' % x)
        print('     ⇒ **可以拿其中一个与 ODD 集同几何跑自协调三臂了。**')
    else:
        print('  ⇒ ⚠ 集2 也没过 ⇒ 需再调（缩板条 / 放盒）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
