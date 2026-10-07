#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r106_pairread.py —— 读 R104 的 PAIR 集间距扫描：`nf2(t=0)` 判据。"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
TAGS = ['pg900', 'pg1000', 'pg1100']


def main():
    print('=' * 96)
    print('_r106 —— PAIR 集（`{1..6}`）间距扫描：`nf2(t=0)`')
    print('=' * 96)
    print('  %-9s %-8s %-8s %-10s %-10s %s'
          % ('tag', 'gap', 'N', 'nf2(t=0)', 'nblk_sig', '判定'))
    ok = []
    for t in TAGS:
        p = os.path.join(MB, 'dry_' + t, 'series.csv')
        mj = os.path.join(MB, 'dry_' + t, 'meta.json')
        if not os.path.exists(p):
            print('  %-9s （未跑完/无数据）  log: %s'
                  % (t, 'yes' if os.path.exists(os.path.join(
                      HERE, '_w2_r104_%s.log' % t)) else 'no'))
            continue
        rows = list(csv.DictReader(open(p)))
        r0 = rows[0]
        meta = json.load(open(mj)) if os.path.exists(mj) else {}
        ea = meta.get('exp_args', {}) or {}
        try:
            nf2 = int(float(r0.get('nf2')))
        except (TypeError, ValueError):
            nf2 = -1
        good = nf2 == 0
        if good:
            ok.append((t, ea.get('block_gap_nm')))
        print('  %-9s %-8s %-8s %-10s %-10s %s'
              % (t, ea.get('block_gap_nm'), meta.get('N'), nf2,
                 r0.get('nblk_sig'), '✅ **分离**' if good else '❌ 已接触'))
    print()
    # 若都失败，看错误信息
    for t in TAGS:
        L = os.path.join(HERE, '_w2_r104_%s.log' % t)
        if os.path.exists(L):
            txt = open(L, encoding='utf-8', errors='replace').read()
            for line in txt.splitlines():
                if 'ValueError' in line or 'exceeds domain' in line:
                    print('  %-9s %s' % (t, line.strip()[:110]))
                    break
    print()
    if ok:
        best = max(ok, key=lambda x: x[1] or 0)
        print('  ⇒ **可用：%s**（其中最大间距 %s nm）' % (ok, best[1]))
    else:
        print('  ⇒ ⚠ 没有分离的 ⇒ 继续减小间距或板条。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
