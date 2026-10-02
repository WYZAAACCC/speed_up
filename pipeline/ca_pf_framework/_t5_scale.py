#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_scale.py --- ★★★★★ **判据 ③④⑤⑥ 的时间尺度**：查 abA 里它们**第一次**满足是哪一步

## 为什么这一条最值钱
新长跑要跑多久才可能满足判据，**不该猜** —— abA 有 298 行、跑到 5922 步，
**直接问它**："块数 >1、`nf2`>0、碰壁、多变体，各在第几步第一次出现？"
⇒ 这就是新长跑的**时间预算依据**。
"""
import csv
import os

P = '_exp/_bk_mb/dry_abA/series.csv'
rows = list(csv.DictReader(open(P, encoding='utf-8', errors='replace')))


def num(r, k):
    try:
        return float((r.get(k) or '').strip())
    except ValueError:
        return None


EV = [
    ('③ 块数 nblk_sig ≥ 2', lambda r: (num(r, 'nblk_sig') or 0) >= 2),
    ('③ 块内低角晶界 nf3 > 0', lambda r: (num(r, 'nf3') or 0) > 0),
    ('③ 多列 nf3_col ≥ 2', lambda r: (num(r, 'nf3_col') or 0) >= 2),
    ('④ **块间界面 nf2 > 0**', lambda r: (num(r, 'nf2') or 0) > 0),
    ('④ 块间界面 nf2 ≥ 100', lambda r: (num(r, 'nf2') or 0) >= 100),
    ('⑤ 碰到盒面 box_touch = 1', lambda r: (num(r, 'box_touch') or 0) == 1),
    ('⑤ 填充 ≥ 1%', lambda r: (num(r, 'Vt') or 0) / 3.0679e-16 >= 0.01),
    ('⑤ 填充 ≥ 5%', lambda r: (num(r, 'Vt') or 0) / 3.0679e-16 >= 0.05),
    ('⑥ 多变体 n_var_sig ≥ 2', lambda r: (num(r, 'n_var_sig') or 0) >= 2),
    ('⑥ 自协调 r_selfac < 1', lambda r: (num(r, 'r_selfac') or 1) < 1.0),
    ('⑥ 自协调 r_selfac ≤ 0.5', lambda r: (num(r, 'r_selfac') or 1) <= 0.5),
]
print('=' * 96)
print('abA（归档基线，N=112 / 7.0 µm / 5922 步 / %d 行）里各判据**首次满足**的步' % len(rows))
print('=' * 96)
print('  %-30s %-10s %s' % ('事件', '首次 step', '末值'))
print('  ' + '-' * 76)
last = rows[-1]
for name, fn in EV:
    hit = next((int(r['step']) for r in rows if fn(r)), None)
    print('  %-30s %-10s %s' % (name, hit if hit is not None else '**从未**',
                                (last.get(name.split()[-1]) or '')[:18]))
print()
print('  ── 末态一览 ──')
for k in ('step', 'Vt', 'nblk_sig', 'blk_laths', 'nf3', 'nf3_col', 'nf2',
          'f_var', 'n_var_sig', 'r_selfac', 'box_touch', 'box_touch_core',
          'blk_alen_nm', 'blk_wlen_nm', 'blk_span_nm'):
    print('     %-16s = %s' % (k, (last.get(k) or '')[:60]))
print()
vt = num(last, 'Vt') or 0
print('  ★ abA 末态填充分数 = %.2f%%（它跑了 5922 步、用 23 个形核）' % (100 * vt / 3.0679e-16))
print('=' * 96)
