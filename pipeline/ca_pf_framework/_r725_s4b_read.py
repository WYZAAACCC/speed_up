#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r725_s4b_read.py <root> —— S4-B（λ 敏感性）的读数汇总（**只读** `series.csv`）。

判据（`_r725_s4b_f2.py` docstring 已先登记）：
  F11-2  λ 增大 ⇒ 块数 / `nf2`（异变体界面数）/ F2 面积 出现**可辨**变化
  F11-3  五臂 `box_touch = 0`
⚠ 只报读数，**不预设方向**；并显式报"哪些列在五臂间**逐位相同**"（= 无效应）。
"""
import csv
import os
import sys


def main():
    root = sys.argv[1]
    # tag 可由命令行给（默认旧的 5 档命名）
    if len(sys.argv) > 2:
        tags = sys.argv[2:]
    else:
        tags = ['f2_lam0', 'f2_lam25', 'f2_lam50', 'f2_lam75', 'f2_lam100']
    data, hdr = {}, None
    for t in tags:
        p = os.path.join(root, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('⚠ 缺 %s' % p)
            continue
        with open(p, newline='') as f:
            rd = csv.DictReader(f)
            hdr = rd.fieldnames
            rows = list(rd)
        if rows:
            data[t] = rows[-1]
    if not data or hdr is None:
        print('⛔ 无数据')
        return 1
    tags = [t for t in tags if t in data]
    print('=' * 104)
    print('S4-B（`--f2-pair-gamma` λ 敏感性）末行读数  root=%s' % root)
    print('=' * 104)

    show = [c for c in hdr if c in (
        'step', 'box_touch', 'nslab_n', 'nf3_col', 'Vt', 'M')]
    for c in ('nf2', 'f2_area_m2', 'nf2_col', 'nblk_sig', 'n_var_sig',
              'blk_laths', 'ncompbig_max', 'n_occ'):
        if c in hdr:
            show.append(c)
    print('  %-22s' % '列' + ''.join('%12s' % t.replace('f2_lam', 'λ=') for t in tags))
    for c in show:
        vals = [data[t].get(c, '') for t in tags]
        same = len(set(vals)) == 1
        print('  %-22s' % c + ''.join('%12s' % (v[:11] if v else '—') for v in vals)
              + ('   ← 五臂**逐位相同**' if same else '   ← **有变化**'))

    print('\n## ★ 哪些列在五臂间**完全不变**（= 该通道对这些量无效应）')
    unchanged, changed = [], []
    for c in hdr:
        if c in ('wall_s', 't_s', 'step'):
            continue
        vals = [data[t].get(c, '') for t in tags]
        (unchanged if len(set(vals)) == 1 else changed).append(c)
    print('  不变列数 = %d / %d' % (len(unchanged), len(unchanged) + len(changed)))
    print('  有变化列：%s' % (', '.join(changed[:24]) if changed else '**一个都没有**'))
    if changed:
        print('\n## ★ 有变化的列（逐档）')
        for c in changed[:14]:
            print('  %-18s' % c
                  + '  '.join('%s=%s' % (t.replace('f2_lam', 'λ'), data[t].get(c, '')[:10])
                              for t in tags))
    return 0


if __name__ == '__main__':
    sys.exit(main())
