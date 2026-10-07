#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_prog.py —— 只读的进度查看器（`M` 因果实验的两臂）。

用途：`R706`/`R707 §4` 的 `Mlo3`(M=3) / `Mhi12`(M=12) 重跑期间看进度。
零副作用：只读 `series.csv` 的**行数与末行**，不解析物理量（那要用 `_b2_meas.py`）。
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_exp', '_bk_block')
TAGS = sys.argv[1:] or ['dry_Mlo3', 'dry_Mhi12']

for t in TAGS:
    p = os.path.join(ROOT, t, 'series.csv')
    if not os.path.exists(p):
        print('%-12s 尚无 series.csv' % t)
        continue
    with open(p) as f:
        rows = [ln for ln in f.read().split('\n') if ln.strip()]
    hdr = rows[0].split(',')
    last = rows[-1].split(',')
    step = last[0] if last else '?'
    ncell = ''
    for key in ('nslab_n', 'M', 'Vt', 'nf3_col'):
        if key in hdr:
            ncell += '  %s=%s' % (key, last[hdr.index(key)])
    print('%-12s %4d 行  末 step=%s%s' % (t, len(rows) - 1, step, ncell))
