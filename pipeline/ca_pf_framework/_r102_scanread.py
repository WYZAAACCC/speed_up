#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r102_scanread.py —— 读 `_r100` 几何扫描的 **`nf2(t=0)`**（唯一的判据）。

判据：`nf2(t=0) == 0` ⟺ 6 个块**真正分离**。
`nf2` 来自 `series.csv` 的**首行**（`--steps 20` ⇒ 首行就是 step 0）
⇒ 覆盖**所有**异变体对（比 `_bk_exp.py` 只比块 0/块 1 的"精确判据"更严）。
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
TAGS = ['sgA', 'sgB', 'sgC', 'sgE', 'sgD', 'sgF', 'sgG', 'sgH']


def main():
    print('=' * 104)
    print('_r102 —— R100 六块几何扫描：`nf2(t=0)` 判读')
    print('=' * 104)
    print('  %-7s %-5s %-7s %-6s %-7s %-11s %-9s %-9s %s'
          % ('tag', 'N', 'L(nm)', 'W', 'gap', 'nf2(t=0)', 'nblk_sig',
             'blk_laths', '判定'))
    ok = []
    for t in TAGS:
        d = os.path.join(MB, 'dry_' + t)
        p = os.path.join(d, 'series.csv')
        mj = os.path.join(d, 'meta.json')
        if not os.path.exists(p):
            print('  %-7s （未跑/未完成）' % t)
            continue
        rows = list(csv.DictReader(open(p)))
        r0 = rows[0]
        meta = json.load(open(mj)) if os.path.exists(mj) else {}
        ea = meta.get('exp_args', {}) or {}
        nf2 = r0.get('nf2', '')
        try:
            nf2v = int(float(nf2))
        except (TypeError, ValueError):
            nf2v = -1
        good = (nf2v == 0)
        if good:
            ok.append(t)
        print('  %-7s %-5s %-7s %-6s %-7s %-11s %-9s %-9s %s'
              % (t, meta.get('N'), ea.get('plate_L'), ea.get('plate_W'),
                 ea.get('block_gap_nm'), nf2, r0.get('nblk_sig'),
                 r0.get('blk_laths'),
                 '✅ **分离**' if good else '❌ 已接触'))
    print()
    if ok:
        print('  ⇒ **可用的构型：%s**（`nf2(t=0) == 0`）' % ok)
        print('     ⇒ 下一步用它的 (N, L, W, gap) 去跑真正的自协调臂。')
    else:
        print('  ⇒ ⚠ **本批没有一个是分离的** ⇒ 需要继续缩小板条 / 放大盒子。')
        print('     按 `nf2(t=0)` 的大小排序即可知道往哪个方向调（越小越接近分离）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
