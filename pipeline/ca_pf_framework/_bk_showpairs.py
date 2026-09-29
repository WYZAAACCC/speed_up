#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_showpairs.py —— 打印 `series.csv` 的**逐对 F3 面积**随时间的变化。

为什么需要：`f3_area` 只有**总量**，而"总量掉"看不出是**哪几对**在掉
（本仓库 R18 就是靠逐对数据才把机理照出来的）。
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
        print('--- %s' % d)
        print('   %-7s %-9s %-7s %-6s %s' % ('step', 'Vt(µm³)', 'f3(µm²)',
                                             'nslab', '逐对 A/µm²'))
        for r in rows:
            fp = (r.get('f3_pairs') or '').strip()
            if not fp:
                continue
            pairs = []
            for tok in fp.split('/'):
                if ':' in tok:
                    k, v = tok.split(':')
                    try:
                        pairs.append((k, float(v)))
                    except ValueError:
                        pass
            pairs.sort(key=lambda x: -x[1])
            print('   %-7s %-9s %-7s %-6s %s'
                  % (r['step'], ('%.4f' % (float(r['Vt']) * 1e18)),
                     ('%.4f' % (float(r['f3_area_m2']) * 1e12)),
                     r['nslab_n'],
                     '  '.join('%s=%.3f' % t for t in pairs) or '（无）'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
