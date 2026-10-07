#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r397_blkt.py —— `blk_nprof` 与 `nf3` 的**逐行轨迹** ⇒ 块结构在早期到底退化了没有。

`blk_nprof` = 每块柱剖面里"出没过"的场数（主口径，`_bk_measure.blocks`）。
若它在 step 20 掉到 1 ⇒ **两根板条在投影下合并成一根**，块结构退化；
若一直保持 2 ⇒ 块结构始终成立，F3 的塌缩只是**界面计数口径**的问题。
"""
from __future__ import annotations

import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def main():
    arms = sys.argv[1:] or ['saSet2', 'saSet2P0', 'permB1_400', 'saSet2DT200']
    for tag in arms:
        p = os.path.join(MB, 'dry_' + tag, 'series.csv')
        if not os.path.exists(p):
            print('%-14s ⚠ 无 series.csv' % tag); continue
        R = list(csv.DictReader(io.open(p, encoding='utf-8')))
        has = 'blk_nprof' in R[0]
        print('=' * 88)
        print('### %s   （有 blk_nprof 列：%s）' % (tag, has))
        if not has:
            print('  ⚠ 本文件早于 R76 接线（P1-33）⇒ 逐块判据无法从它读')
            continue
        print('  %-6s %-26s %-8s %-8s %s' % ('step', 'blk_nprof', 'nf3', 'nblk_sig', 'blk_vars'))
        for i, r in enumerate(R):
            if i % max(len(R) // 14, 1) and i != len(R) - 1:
                continue
            print('  %-6s %-26s %-8s %-8s %s'
                  % (r.get('step'), r.get('blk_nprof', ''), r.get('nf3', ''),
                     r.get('nblk_sig', ''), r.get('blk_vars', '')))
        # 统计 blk_nprof 里出现过 "1" 的行数
        bad = sum(1 for r in R if '1' in str(r.get('blk_nprof', '')).split('/'))
        print('  ⇒ `blk_nprof` 里出现 "1"（某块只剩一根板条）的行数 = **%d / %d**'
              % (bad, len(R)))


if __name__ == '__main__':
    sys.exit(main())
