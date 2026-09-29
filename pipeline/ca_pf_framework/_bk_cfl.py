#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_cfl.py —— 读若干算例 `series.csv` 的 **CFL 实际用量**列 `cfl_used`
（= `dt·M·dG_max/dx`，单位：胞/步）并对照 CFL 目标 0.15。

为什么要单独一个文件：这一列是 R29 新加的，判据是
「**实际每步最大位移不得超过 CFL 目标太多**」——
而本仓库已有前车之鉴（`suggest_dt` 的 docstring：只按化学驱动力定 dt
实测会让界面每步走到 0.6–0.75 dx，超 CFL 4–5 倍，剖面失真）。
PowerShell → wsl → awk 的引号会被吃三层，故写成文件。
"""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    dirs = argv[1:] or ['_exp/_bk_closed/gpos_clctrl']
    for d in dirs:
        p = os.path.join(_HERE, d, 'series.csv')
        if not os.path.exists(p):
            print('%-38s （无 series.csv）' % d)
            continue
        rows = list(csv.DictReader(open(p)))
        if not rows or 'cfl_used' not in rows[0]:
            print('%-38s ⚠ **没有 cfl_used 列**（该算例在 R29 加列之前起跑）' % d)
            continue
        v = []
        for r in rows:
            try:
                x = float(r['cfl_used'])
            except (TypeError, ValueError):
                continue
            if x == x:
                v.append((int(r['step']), x))
        if not v:
            print('%-38s cfl_used 全是 nan' % d)
            continue
        xs = [x for _, x in v]
        print('%-38s 测点=%d  **max cfl_used = %.4f 胞/步**  min=%.4f  末值=%.4f'
              % (d, len(v), max(xs), min(xs), xs[-1]))
        bad = [(s, x) for s, x in v if x > 0.15 * 1.5]
        print('%-38s 超 CFL 目标 1.5 倍的测点: %s'
              % ('', ('无' if not bad else
                      ', '.join('step%d:%.3f' % b for b in bad[:8]))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
