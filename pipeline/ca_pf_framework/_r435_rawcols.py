#!/usr/bin/env python3
"""_r435_rawcols.py —— 先看 `vols` / `ths` / `runs` 的**原始字符串**长什么样。

⚠ 自纠错（`§` 待记）：`_r434` 的 `parse_list()` 把 `vols` 解析成**空列表**，
而它的 P-1 正对照写成 `if v and vt > 0` ⇒ **空列表直接被跳过** ⇒
"相对差 >5% 的行数 = 0/30" 是**空洞的通过**（vacuous pass）。
⇒ 本脚本先把原始串打出来再写解析器（`AGENTS.md` 教训 29：先 head 看原始文本再写正则）。
"""
import csv
import os

BASE = '_exp/_bk_mb'

for tag in ('dry_abA', 'dry_abB'):
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        print('[%s] ✗ 无' % tag)
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    print('=' * 90)
    print('[%s] 行数=%d' % (tag, len(rows)))
    for col in ('vols', 'ths', 'runs', 'f3_pairs'):
        if col not in rows[0]:
            print('  %-10s ✗ 不在列里' % col)
            continue
        print('  %-10s 原始值（前 2 行，repr 截断 200 字符）：' % col)
        for r in rows[:2]:
            v = r.get(col, '')
            print('      step=%-5s %r' % (r.get('step'), v[:200]))
        print('      长度分布：%s'
              % sorted({len(r.get(col, '')) for r in rows})[:8])
