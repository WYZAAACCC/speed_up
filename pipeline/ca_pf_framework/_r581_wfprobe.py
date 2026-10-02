#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_wfprobe.py --- ★★★★★ 摸清"怎么才能把 `t_wf` 真正算出来"（三条路）"""
import csv
import os
import sys

import numpy as np

FR = os.path.dirname(os.path.abspath(__file__))


def main():
    print('=' * 100)
    print('① `t_wf` 是否已经在 `series.csv` 的列里？')
    print('=' * 100)
    for tag in ('BK6', 'BK7'):
        p = '_exp/_bk_blk/dry_%s/series.csv' % tag
        if not os.path.exists(p):
            continue
        hdr = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')).__next__().keys())
        hits = [h for h in hdr if 't_wf' in h or 'wf' in h or 'thick' in h]
        print('  %-5s 共 %d 列；与"宽面厚度"有关的列 = %s'
              % (tag, len(hdr), hits if hits else '**无**'))
    print()
    print('=' * 100)
    print('② 快照里那几个 `band_*` 键是什么（是不是 φ 的载体）？')
    print('=' * 100)
    p = '_exp/_bk_blk/dry_BK6/snap_00250.npz'
    if not os.path.exists(p):
        print('  ⚠ 没有 %s' % p)
        return
    z = np.load(p)
    for k in z.files:
        a = z[k]
        try:
            extra = ''
            if a.dtype.kind in 'fiu' and a.size:
                extra = '  最小=%.4g 最大=%.4g' % (float(np.min(a)), float(np.max(a)))
            print('  %-14s shape=%-20s dtype=%-10s%s' % (k, str(a.shape), str(a.dtype), extra))
        except Exception as e:
            print('  %-14s shape=%-20s dtype=%-10s（%s）' % (k, str(a.shape), str(a.dtype), e))
    print()
    print('=' * 100)
    print('③ `wide_face_thickness` 有没有被**接线**（谁调它）？')
    print('=' * 100)
    for fn in ('_bk_measure.py', '_bk_exp.py', '_bk_closure.py'):
        fp = os.path.join(FR, fn)
        if not os.path.exists(fp):
            continue
        for i, l in enumerate(open(fp, encoding='utf-8', errors='replace'), 1):
            if 'wide_face_thickness' in l or 't_wf' in l:
                print('  %-18s:%-5d %s' % (fn, i, l.strip()[:110]))
    print()
    print('=' * 100)
    print('④ 引擎能不能把 `φ` 存进快照（找 `snap` 的写法）？')
    print('=' * 100)
    fp = os.path.join(FR, '_bk_exp.py')
    for i, l in enumerate(open(fp, encoding='utf-8', errors='replace'), 1):
        if 'savez' in l or ('snap' in l.lower() and 'phi' in l.lower()):
            print('  :%-5d %s' % (i, l.strip()[:110]))


if __name__ == '__main__':
    main()
