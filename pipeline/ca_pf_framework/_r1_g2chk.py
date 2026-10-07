#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_g2chk.py --- G-2 报警的诊断：单核为什么会出现第 2 个连通分量？

G-2 的定义（`_r1_exp.py:42`）：目标变体分成 >1 个连通分量 ⇒ **`max−min` 读数被碎片绑架**。
`mid192_ns4`（实验 3，R24 标准单核）在 step 176/180 打出了 `⚠G-2分量2`。

要分清两种可能：
  (a) **数值碎屑**（小液滴）：占体积比极小（<1%），`max−min` 几乎不受影响；
  (b) **真裂分**：第 2 个分量与主分量同量级 ⇒ 单核实验根本不成立。

判据：看 `nsig`（≥1% 的分量数）、`debris`、`big_frac`（最大分量占比）、
以及被污染前后 `L_cal` 的**跳变**。若 `big_frac` 仍 ≈1 且 `debris` 小 ⇒ (a)。
"""
import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
WS = ['ncomp', 'nsig', 'debris', 'big_frac', 'fill_cal', 'L_cal', 'W_cal',
      'T_cal', 'LW_cal', 'LT_cal', 'ncell']
for d in (sys.argv[1:] or ['mid192_ns4']):
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('%s: 无 CSV' % d); continue
    rows = list(csv.DictReader(open(p)))
    print('=' * 96)
    print('%s  （%d 行）' % (d, len(rows)))
    print('%6s %8s %7s %7s %9s %9s %10s %10s'
          % ('row', 'ncomp', 'nsig', 'debris', 'big_frac', 'fill_cal',
             'L_cal(nm)', 'LW_cal'))
    for i, r in enumerate(rows):
        if i < len(rows) - 12:
            continue
        def g(k):
            try:
                return float(r[k])
            except (ValueError, KeyError, TypeError):
                return float('nan')
        print('%6d %8s %7s %7.4f %9.4f %9.4f %10.1f %10.3f'
              % (i * 4, r.get('ncomp'), r.get('nsig'), g('debris'),
                 g('big_frac'), g('fill_cal'), g('L_cal') * 1e9, g('LW_cal')))
    # G-2 出现的位置
    bad = [i * 4 for i, r in enumerate(rows)
           if r.get('ncomp') not in (None, '', '1', '1.0')]
    print('  G-2（ncomp>1）出现在 step：%s' % (bad if bad else '无'))
    if bad:
        print('  首次出现前的最后一行 L_cal=%.1f nm，出现后=%.1f nm'
              % (float(rows[bad[0] // 4 - 1]['L_cal']) * 1e9,
                 float(rows[bad[0] // 4]['L_cal']) * 1e9))
print('=' * 96)
