#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r145_thrtime.py —— 从 `_r143` 的日志读步时（T-2 参考值）。

⚠ 记账：本机是 **DRAM 带宽瓶颈**（`§7.2c`），而且这些跑的时候
`R139`/`R141` **四条重臂在并发** ⇒ 步时**只作参考**，不是干净的加速比曲线。
"""
from __future__ import annotations

import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'\[\s*(\d+)\].*?\|\s*([\d.]+)s/步')


def main():
    print('=' * 92)
    print('_r145 —— `--nthreads` 的步时（T-2 参考值）')
    print('=' * 92)
    print('  %-10s %-9s %-13s %-13s %s'
          % ('nthreads', '读数个数', '步时中位(s)', '步时最小(s)', '相对串行（中位）'))
    base = None
    out = []
    for nt in (1, 2, 4, 8):
        p = os.path.join(HERE, '_w2_r143_t%d.log' % nt)
        if not os.path.exists(p):
            print('  %-10d （无日志）' % nt)
            continue
        txt = open(p, encoding='utf-8', errors='replace').read()
        ts = [float(m.group(2)) for m in PAT.finditer(txt)]
        if not ts:
            print('  %-10d （无步时读数）' % nt)
            continue
        med = float(np.median(ts))
        if base is None:
            base = med
        out.append((nt, len(ts), med, min(ts), med / base))
        print('  %-10d %-9d %-13.3f %-13.3f %.3f×'
              % (nt, len(ts), med, min(ts), med / base))
    print()
    if out:
        print('  ⇒ 从 1 到 %d 线程：步时 %.3f → %.3f s（**%.2f×**）'
              % (out[-1][0], out[0][2], out[-1][2],
                 out[0][2] / max(out[-1][2], 1e-9)))
        print('     ⚠ **不是**干净的加速比：R139/R141 四条重臂同时在跑（DRAM 争用），')
        print('       而且 N=64 太小（固定开销占比高）⇒ 这个数只说明"并行没坏"。')
    print()
    print('  ---- 与既有结论对照 ----')
    print('     `R30_AUDIT_LEDGER` §7.2c 的立场是：本机 **DRAM 带宽瓶颈**，')
    print('     并行的价值在"内存够时能同时跑多条臂"，不在单臂加速。')
    print('     ⇒ 本轮 T-1 的**逐位一致**才是要的东西（正确性）；')
    print('       加速比要看 **R141 两臂并发 vs 单臂**的墙钟（下轮可从 `wall_s` 读）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
