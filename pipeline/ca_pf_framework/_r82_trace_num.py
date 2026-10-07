#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r82_trace_num.py —— **数字溯源**：全库扫 `series.csv` 的 `r_selfac` 末值，
找出 `R30_AUDIT_LEDGER.md §16` 里 seed-37 那两个数（0.5097 / 0.6437）到底出自哪个运行目录。

为什么必须做（本仓库硬纪律）：「写进文档的每个数字都要能溯源到脚本名或运行目录」。
实测：`eng_mb2c`/`eng_mb3c` 的末值复算 = 0.499761 / 0.594472，
而台账 §16 的 seed-37 行写的是 0.5097 / 0.6437。**对不上就必须查清是谁错了。**
"""
from __future__ import annotations

import csv
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOTS = [os.path.join(HERE, '_exp')]


def main():
    want = [float(x) for x in (sys.argv[1:] or ['0.5097', '0.6437'])]
    print('=' * 108)
    print('_r82_trace_num —— 全库扫 `r_selfac` 末值，找 %s 的出处' % want)
    print('=' * 108)
    hits = {w: [] for w in want}
    n = 0
    allrows = []
    for root in ROOTS:
        for p in glob.glob(os.path.join(root, '**', 'series.csv'), recursive=True):
            try:
                rows = list(csv.DictReader(open(p)))
            except Exception:
                continue
            if not rows or 'r_selfac' not in rows[0]:
                continue
            vals = [r['r_selfac'] for r in rows if r.get('r_selfac') not in ('', None)]
            if not vals:
                continue
            n += 1
            v0, v1 = float(vals[0]), float(vals[-1])
            allrows.append((os.path.relpath(p, HERE), v0, v1, len(rows),
                            rows[-1].get('step'), rows[-1].get('n_var_sig'),
                            rows[-1].get('f_var')))
            for w in want:
                if abs(v0 - w) < 5e-4:
                    hits[w].append((os.path.relpath(p, HERE), '首值', v0))
                if abs(v1 - w) < 5e-4:
                    hits[w].append((os.path.relpath(p, HERE), '末值', v1))
                # ★ 也必须找**中间步** —— 台账可能引的是中途读数（本仓库真发生过：
                #   §76 就是拿"跑了一半的读数"当结论，后来被终态否掉）。
                for i, s in enumerate(vals):
                    try:
                        sv = float(s)
                    except ValueError:
                        continue
                    if abs(sv - w) < 5e-4:
                        hits[w].append((os.path.relpath(p, HERE),
                                        '第%d行(step %s)' % (i, rows[i].get('step')),
                                        sv))
                        break
    print('  扫到 %d 个带 `r_selfac` 的 series.csv' % n)
    print()
    for w in want:
        print('  **%s**：%d 处命中' % (w, len(hits[w])))
        for p, kind, v in hits[w][:12]:
            print('     %-6s %.6f  %s' % (kind, v, p))
        print()
    print('  ---- 与 §16 三行对照（`mb2*` / `mb3*` 族全部打印）----')
    print('  %-42s %-10s %-10s %-6s %-7s %s'
          % ('目录', 'r 首值', 'r 末值', '行数', '末步', 'n_var_sig/f_var'))
    for p, v0, v1, nr, st, nvs, fv in sorted(allrows):
        if 'mb2' in p or 'mb3' in p:
            print('  %-42s %-10.6f %-10.6f %-6d %-7s %s | %s'
                  % (p.replace('_exp/_bk_mb/', ''), v0, v1, nr, st, nvs, fv))
    print()
    print('  ⇒ §16 记的 seed-37: ed 0.5097 / random 0.6437。')
    print('     若上面 **没有任何** 目录的末值等于这两个数 ⇒ 台账数字**无法溯源**，')
    print('     必须按 F 盘原始数据改正（方向若不变，8/9 的判定则不受影响）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
