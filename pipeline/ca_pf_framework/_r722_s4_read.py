#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r722_s4_read.py <root> <tag> [tag ...] —— S4-A 的读数汇总（**只读** `series.csv`）。

判据（`_r722_s4_omega.py` docstring 已先登记）：
  F10-2  同一步比较 `f3_area` / `nf3_col`，看 `perstep` 是否削弱 M 依赖
  F10-3  四臂 `nslab_n ≥ 2`
  ★ 另外报 `box_touch`（`R720 §1`：跨臂比较必须都在安全区间）
"""
import csv
import os
import sys


def read(path):
    with open(path, newline='') as f:
        rd = csv.DictReader(f)
        return rd.fieldnames or [], list(rd)


def f(row, key):
    try:
        return float(row[key])
    except (KeyError, ValueError, TypeError):
        return float('nan')


def main():
    root, tags = sys.argv[1], sys.argv[2:]
    print('=' * 100)
    print('S4-A（`--omega-mode`）读数汇总  root=%s' % root)
    print('=' * 100)
    print('  %-14s %6s %8s %9s %10s %10s %12s' %
          ('tag', 'step', 'M', 'nslab_n', 'nf3_col', 'F3面积', 'box_touch'))
    for t in tags:
        p = os.path.join(root, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('  %-14s  ⚠ 无 series.csv' % t)
            continue
        hdr, rows = read(p)
        if not rows:
            continue
        r = rows[-1]                      # 末行 = 本臂终点
        area_key = next((k for k in hdr if k.startswith('f3_area')), None)
        print('  %-14s %6s %8s %9s %10s %10s %12s'
              % (t[:14], r.get('step', '?'), r.get('M', '?'),
                 r.get('nslab_n', '?'), r.get('nf3_col', '?'),
                 ('%.6g' % f(r, area_key)) if area_key else '—',
                 r.get('box_touch', '?')))
    print()
    print('  ⚠ 判读：`F3面积` 单位 m^2；`box_touch` 必须为 0 才能做形状/面积比较。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
