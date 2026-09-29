#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_v8b.py —— R30：核实 V-8b 的**时间基不一致**（CSV 末行 vs 最后快照）。"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for d in sys.argv[1:] or ['_exp/_bk_closed/dry_cln11']:
    p = os.path.join(HERE, d, 'series.csv')
    if not os.path.exists(p):
        print('%s 无 series.csv' % d)
        continue
    rows = list(csv.DictReader(open(p, newline='', encoding='utf-8')))
    snaps = sorted(glob.glob(os.path.join(HERE, d, 'snap_*.npz')))
    last = rows[-1]
    vols = [t for t in last.get('vols', '').split('/')]
    present = [k for k, v in enumerate(vols, start=1)
               if v.strip() and float(v) > 0]
    st_snap = os.path.basename(snaps[-1]) if snaps else '（无）'
    print('%-34s CSV 末行 step=%-6s  在位的场=%s'
          % (d, last.get('step'), present))
    print('%-34s 最后一个快照 = %s' % ('', st_snap))
    # 找快照那一步的 CSV 行
    try:
        sstep = int(st_snap.split('_')[1].split('.')[0])
    except Exception:
        sstep = None
    if sstep is not None:
        row = None
        for r in rows:
            try:
                if int(float(r['step'])) == sstep:
                    row = r
            except (TypeError, ValueError):
                pass
        if row is not None:
            v2 = [t for t in row.get('vols', '').split('/')]
            pres2 = [k for k, v in enumerate(v2, start=1)
                     if v.strip() and float(v) > 0]
            print('%-34s 该快照步的 CSV 行在位的场=%s' % ('', pres2))
            if pres2 != present:
                print('   ⛔ **两套"在位场"不同** ⇒ V-8b 用 CSV 末行定 `present`、'
                      '却用**最后快照**量厚度 ⇒ 时间基不一致')
            else:
                print('   ✓ 两套一致（本次没有错位）')
