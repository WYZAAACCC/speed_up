#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_csv.py —— 只读：把 `series.csv` 里指定的列按行打出来（用于量化趋势）。

用法：
  python3 _r30_csv.py _exp/_bk_closed/dry_cl1b/series.csv step,Vt,nslab_n,f3_pos_dx,n_lath,a_lath,box_touch
  python3 _r30_csv.py <csv> --head 5
"""
import sys
import csv


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    path, cols = sys.argv[1], sys.argv[2].split(',')
    nhead = None
    if '--head' in sys.argv:
        nhead = int(sys.argv[sys.argv.index('--head') + 1])
    with open(path) as fh:
        rows = list(csv.DictReader(fh))
    print('行数 = %d；列 = %s' % (len(rows), ','.join(cols)))
    print('  ' + '  '.join('%14s' % c for c in cols))
    show = rows[:nhead] if nhead else rows
    for r in show:
        out = []
        for c in cols:
            v = r.get(c, '')
            try:
                f = float(v)
                out.append('%14.6g' % f)
            except (TypeError, ValueError):
                out.append('%14s' % (v if v is not None else ''))
        print('  ' + '  '.join(out))


if __name__ == '__main__':
    main()
