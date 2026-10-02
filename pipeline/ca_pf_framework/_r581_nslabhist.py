#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_nslabhist.py --- ★★★★★★ `nslab_n` 的**历史**：它是不是对"新变体"**不敏感**？

## 背景（R149 的发现）
F：step 100 时 3-D=13、`nslab_n`=13（相等）；step 200 时 3-D=22、`nslab_n`=14（差 8）。
**⇒ 若 `nslab_n` 在 step 125–200 之间**一直**是 14，而 3-D 在涨 ⇒ 它**不是"低报"，
而是**对新增的变体完全不敏感****（1-D 柱只穿过原来那一条柱）。

## 本脚本
把 `nslab_n` / `nf3_col` / `nf3` / `Vt` 的**整条历史**打出来（每 5 步一行）
⇒ 看 `nslab_n` 是"阶梯上升"还是"**卡住**"。
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_mn64'
TAGS = sys.argv[2:] or ['F', 'G', 'E']
COLS = ['nslab_n', 'nf3_col', 'nf3', 'nf2', 'Vt']


def main():
    for t in TAGS:
        p = os.path.join(ROOT, 'dry_' + t, 'series.csv')
        if not os.path.exists(p):
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        if not rows:
            continue
        hdr = list(rows[0].keys())
        kstep = hdr[0]
        print('=' * 100)
        print('臂 %s：共 %d 行（step %s → %s）' % (t, len(rows), rows[0][kstep], rows[-1][kstep]))
        print('=' * 100)
        print(' %-7s %s' % ('step', ' '.join('%-12s' % c for c in COLS)))
        print(' ' + '-' * 74)
        for r in rows:
            vals = []
            for c in COLS:
                v = r.get(c, '—')
                try:
                    f = float(v)
                    vals.append('%-12.6g' % f)
                except Exception:
                    vals.append('%-12s' % str(v)[:12])
            print(' %-7s %s' % (r[kstep], ' '.join(vals)))
        print()
        # 汇总：nslab_n 的变化
        try:
            ns = [float(r['nslab_n']) for r in rows if r.get('nslab_n') not in ('', None)]
            if ns:
                d = [ns[i + 1] - ns[i] for i in range(len(ns) - 1)]
                print('  ★ `nslab_n`：首 %g → 末 %g；**增量为 0 的步数 = %d / %d**'
                      % (ns[0], ns[-1], sum(1 for x in d if x == 0), len(d)))
                print('  ⇒ 若"增量为 0"占**绝大多数**而末值仍很低 ⇒ **它对新增变体不敏感**')
        except Exception as e:
            print('  （算不出：%s）' % e)
        print()


if __name__ == '__main__':
    main()
