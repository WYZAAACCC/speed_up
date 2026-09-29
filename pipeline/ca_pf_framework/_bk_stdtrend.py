#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_stdtrend.py —— 打印若干算例的 `f3_std_m`（界面平整度）随步数的变化。

为什么需要：`f3_std_n` 在 `series.csv` 里**本来就有列**（`f3_std_m`，单位米），
但本轮我一开始是**从日志行里正则抠**出来的 —— 那是脆的（格式一变就抠不到）。
把它当列读，才能对**归档算例**也量一遍。
"""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    for d in (argv[1:] or ['_exp/_bk_closed/dry_cl1b']):
        p = os.path.join(_HERE, d, 'series.csv')
        if not os.path.exists(p):
            print('（无 %s）' % p)
            continue
        rows = list(csv.DictReader(open(p)))
        if not rows or 'f3_std_m' not in rows[0]:
            print('%-40s ⚠ 没有 f3_std_m 列' % d)
            continue
        print('--- %s' % d)
        out = []
        for r in rows:
            v = r['f3_std_m']
            try:
                x = float(v) * 1e9
            except (TypeError, ValueError):
                continue
            if x == x:
                out.append((int(r['step']), x))
        print('   ' + '  '.join('%d:%.0f' % t for t in out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
