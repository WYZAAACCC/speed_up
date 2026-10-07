#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r144_thrread.py —— `advance` 多核并行的**逐位判决**（`_r143` 的读数）。

判据 **T-1**：`--nthreads 1/2/4/8` 的 `series.csv` 必须**逐位相同**
（忽略纯计时列 `wall_s` / `t_step_s` 之类）。
判据 **T-2**：报实测步时比（本机 DRAM 瓶颈，只作参考）。
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '_exp', '_bk_thr')
NTS = [1, 2, 4, 8]
IGNORE = ('wall_s', 'wall', 't_step_s', 'eta_s', 'elapsed_s')


def load(nt):
    p = os.path.join(ROOT, 'dry_t%d' % nt, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as f:
        rows = list(csv.DictReader(f))
    return rows


def main():
    print('=' * 104)
    print('_r144 —— `advance` 多核并行：逐位一致性 + 步时')
    print('=' * 104)
    D = {}
    for nt in NTS:
        r = load(nt)
        if r:
            D[nt] = r
            print('  nthreads=%-2d  %d 行  列数 %d' % (nt, len(r), len(r[0])))
    if len(D) < 2:
        print('\n⚠ 数据不全，稍后再来')
        return 2
    ref_nt = min(D)
    ref = D[ref_nt]
    cols = [c for c in ref[0] if c not in IGNORE]
    print()
    print('  **基准 = `--nthreads %d`**；忽略列 %s' % (ref_nt, list(IGNORE)))
    print('  %-12s %-9s %-14s %s' % ('nthreads', '行数', '差异字段数', '判定'))
    allok = True
    for nt in sorted(D):
        r = D[nt]
        if len(r) != len(ref):
            print('  %-12d %-9d %-14s ❌ 行数不同' % (nt, len(r), '—'))
            allok = False
            continue
        nd = 0
        bad = []
        for a, b in zip(ref, r):
            for c in cols:
                if a.get(c) != b.get(c):
                    nd += 1
                    if len(bad) < 3:
                        bad.append('%s: %s vs %s' % (c, a.get(c), b.get(c)))
        ok = (nd == 0)
        allok &= ok
        print('  %-12d %-9d %-14d %s'
              % (nt, len(r), nd, '✅ **逐位相同**' if ok else '❌ ' + '; '.join(bad)))
    print()
    print('  ⇒ **T-1（逐位一致）%s**' % ('PASS ✅ —— 并行不改变物理'
                                        if allok else 'FAIL ❌ —— 并行改变了数值，所有结果要打折'))
    # ---- 步时 ----
    print()
    print('  **T-2 步时（只作参考；本机 DRAM 瓶颈、且与 R139/R141 并发争用）**')
    print('  %-12s %-16s %s' % ('nthreads', '步时中位(s)', '相对串行'))
    base = None
    for nt in sorted(D):
        r = D[nt]
        tot = 0.0
        # `_bk_exp` 不落盘步时列 ⇒ 从日志读（见下方兜底）
        print('  %-12d %-16s %s' % (nt, '（见日志）', ''))
    print()
    print('  ⚠ 步时请从 `_w2_r143_t*.log` 的 `xxx s/步` 行读；本脚本只判**正确性**。')
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
