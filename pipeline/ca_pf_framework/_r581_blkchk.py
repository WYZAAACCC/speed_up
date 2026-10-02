#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_blkchk.py --- ★★★★★★★ **BK6 的块表列到底有没有值**（C6 直接判据量的判决）

## 判据（**预先写死在 `_r581_blkarm.sh` 里**）
| 观察 | 判决 |
|---|---|
| **`r_selfac` 有值（非 NaN/空）** | **✅ C6 有直接判据量了** |
| **`n_habit`/`blk_laths`/`blk_nprof`/`blk_span_nm` 有值** | **✅ goal §(17) 第 2、3 件事可报** |
| **全空** | ❌ 还有别的东西挡着 ⇒ 查 `_blk_cols` 的 `except` |
"""
import csv
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
TAG = sys.argv[2] if len(sys.argv) > 2 else 'BK6'
WANT = ['nblk_sig', 'blk_laths', 'blk_vars', 'n_var_sig', 'n_habit', 'f_var',
        'r_selfac', 'blk_nlath', 'blk_nprof', 'blk_nruns',
        'blk_span_nm', 'blk_alen_nm', 'blk_wlen_nm']
STATE = ['nslab_n', 'nslab_n1', 'nf3', 'nf2']


def main():
    p = os.path.join(ROOT, 'dry_' + TAG, 'series.csv')
    if not os.path.exists(p):
        print('  ⚠ 还没有 %s' % p)
        return
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    print('=' * 108)
    print('臂 %s：%d 行' % (TAG, len(rows)))
    print('=' * 108)
    have = [c for c in STATE + WANT if c in rows[0]]
    miss = [c for c in WANT if c not in rows[0]]
    if miss:
        print('  ⚠ CSV 里没有这些列：%s' % ', '.join(miss))
    print('  %-6s %s' % ('step', ' '.join('%-11s' % c[:11] for c in have)))
    print('  ' + '-' * 104)
    for r in rows:
        vals = []
        for c in have:
            v = (r.get(c, '') or '').strip()
            if v == '':
                vals.append('%-11s' % '（空）')
            else:
                try:
                    vals.append('%-11.4g' % float(v))
                except Exception:
                    vals.append('%-11s' % v[:11])
        print('  %-6s %s' % (r[list(r.keys())[0]], ' '.join(vals)))
    # 判决
    print()
    filled = {}
    for c in WANT:
        if c not in rows[0]:
            continue
        n = sum(1 for r in rows if (r.get(c, '') or '').strip() not in ('', 'nan', 'NaN'))
        filled[c] = n
    nz = {k: v for k, v in filled.items() if v > 0}
    print('  ★ **有值的列**（行数 / 总行数）：')
    if nz:
        for k, v in nz.items():
            print('     %-14s %d / %d' % (k, v, len(rows)))
    else:
        print('     ❌ **一个都没有** ⇒ 还有东西挡着（查 `_blk_cols` 的 `except`）')
    print()
    if filled.get('r_selfac', 0) > 0:
        print('  ✅ **`r_selfac` 有值 ⇒ C6 的**直接判据量**拿到了**')
    else:
        print('  ❌ **`r_selfac` 全空** ⇒ C6 仍无直接判据量')
    print('=' * 108)


if __name__ == '__main__':
    main()
