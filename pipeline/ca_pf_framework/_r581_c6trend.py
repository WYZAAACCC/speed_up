#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_c6trend.py --- C6 的两臂趋势（`BK6` 默认 vs `BK7` 驱动）"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
KEYS = ['nslab_n1', 'nf3', 'nf2', 'nblk_sig', 'n_var_sig', 'n_habit', 'r_selfac']


def main():
    for tag in ('BK6', 'BK7'):
        p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('  %s：无数据' % tag)
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        k = list(rows[0].keys())[0]
        print('=' * 88)
        print('臂 %s：%d 行' % (tag, len(rows)))
        print('=' * 88)
        print('  %-6s %s' % ('step', ' '.join('%-12s' % c[:12] for c in KEYS)))
        for r in rows:
            vals = []
            for c in KEYS:
                v = (r.get(c, '') or '').strip()
                if v == '':
                    vals.append('%-12s' % '（空）')
                else:
                    try:
                        vals.append('%-12.5g' % float(v))
                    except Exception:
                        vals.append('%-12s' % v[:12])
            print('  %-6s %s' % (r[k], ' '.join(vals)))
        print()
    print('=' * 88)
    print('★ 看什么：`BK7`（驱动路）的 `nf2`/`n_var_sig`/`n_habit` 会不会**后来涨起来**')
    print('   ⇒ **一直 =0 / =1** ⇒ **驱动路确实是"赢者通吃 ⇒ 单变体"** （C6 更不利）')
    print('   ⇒ **后来涨起来** ⇒ **驱动路也会产生多变体** ⇒ **要重做置换检验**')
    print('=' * 88)


if __name__ == '__main__':
    main()
