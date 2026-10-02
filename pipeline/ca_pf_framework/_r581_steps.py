#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_steps.py --- ★★★★★ **各臂到底跑了多少步**（逐个从 series.csv 读，不凭记忆）"""
import csv
import os
import sys
from collections import OrderedDict

# (根目录, tag, 设计步数, 结局说明)
ARMS = [
    ('_exp/_bk_blk', 'BK6', 250, 'C6 判决臂（默认路）—— **跑完**'),
    ('_exp/_bk_blk', 'BK7', 250, 'C6 判决臂（驱动路）—— **跑完**'),
    ('_exp/_bk_blk', 'BN1', 30, 'C6 负对照（单变体）—— **跑完**'),
    ('_exp/_bk_blk', 'BG2', 60, 'C2 修正实验（细种子）—— **跑完**'),
    ('_exp/_bk_blk', 'BG1', 60, 'C2 作废实验（种子撑满盒）—— **中途停**'),
    ('_exp/_bk_p2', 'p2_m12ov', 4000, 'N=160（10 µm）—— **手工停**'),
    ('_exp/_bk_alloc160', 'TUNED', 30, 'A4 判决（现状档）—— **硬闸杀在构造期**'),
    ('_exp/_bk_alloc160', 'ARENA', 30, 'A4 判决（目标档）—— **看门狗杀在构造期**'),
    ('_exp/_bk_alloc160', 'PLAIN', 30, 'A4 判决（参考档）—— **硬闸杀在构造期**'),
]


def main():
    print('=' * 104)
    print('各臂**实际跑到哪一步**（从 `series.csv` 逐行读）')
    print('=' * 104)
    print('  %-10s %-9s %-9s %-9s %-11s %s' %
          ('臂', '设计步数', '末步', '数据行数', '到达率', '结局'))
    print('  ' + '-' * 100)
    for root, tag, want, note in ARMS:
        p = os.path.join(root, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('  %-10s %-9d %-9s %-9s %-11s %s' % (tag, want, '—', '—', '—', note))
            continue
        rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
        if not rows:
            print('  %-10s %-9d %-9s %-9d %-11s %s' % (tag, want, '0', 0, '0%', note))
            continue
        k = list(rows[0].keys())[0]
        last = rows[-1][k]
        try:
            lastf = float(last)
        except Exception:
            lastf = float('nan')
        cov = (lastf / want * 100.0) if want else float('nan')
        print('  %-10s %-9d %-9s %-9d %-11s %s' %
              (tag, want, last, len(rows), ('%.1f%%' % cov) if cov == cov else '—', note))
    print()
    print('  ★ 说明：`series.csv` 按 `--every N` 落一行 ⇒ **行数 ≈ 末步/every + 1**')
    print('  ★ 而 C5（第二段的生产长跑）**至今一次都没跑**（`--steps 4000` 的那条只到 step 175 就被手工停）')
    print('=' * 104)


if __name__ == '__main__':
    main()
