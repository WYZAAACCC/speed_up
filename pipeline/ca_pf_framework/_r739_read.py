#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r739_read.py <root> <tagA> <tagB> —— T2 的读数（`nf2` 是唯一的成败判据）。

判据（`_r739_T2_stackedg.py` docstring **先登记**）：
  T2-0 正对照：`--stack-pick-dg 0` 复现 `R725` 的症状（`nf2 == 0`）
  T2-1 `--stack-pick-dg 1` 出现 `nf2 ≥ 1`
  T2-3 两臂 `box_touch = 0`
"""
import csv
import os
import sys


def main():
    root, tA, tB = sys.argv[1], sys.argv[2], sys.argv[3]
    print('=' * 100)
    print('T2：`--stack-pick-dg` 能否造出 F2 界面（root=%s）' % root)
    print('=' * 100)
    keys = ['step', 'box_touch', 'nslab_n', 'nf3_col', 'nf2', 'f2_area_m2',
            'n_var_sig', 'nblk_sig', 'blk_laths', 'Vt', 'n_occ']
    tab = {}
    for t in (tA, tB):
        p = os.path.join(root, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('  ⚠ 缺 %s' % p)
            continue
        with open(p, newline='') as f:
            rows = [r for r in csv.DictReader(f) if r.get('step')]
        tab[t] = rows
        print('\n【%s】%d 个测点' % (t, len(rows)))
        ks = [k for k in keys if rows and k in rows[0]]
        print('   ' + ' '.join('%-11s' % k for k in ks))
        for r in rows:
            print('   ' + ' '.join('%-11s' % str(r.get(k, ''))[:11] for k in ks))
    print()
    print('  ## 判定')
    for t, rows in tab.items():
        nf2 = [r.get('nf2', '') for r in rows]
        has = any(str(v).strip() not in ('', '0', '0.0') for v in nf2)
        print('  %-6s `nf2` 逐测点 = %s ⇒ %s'
              % (t, nf2, '✅ **出现 F2 界面**' if has else '⛔ 恒为 0'))
    if tA in tab:
        nf2a = [r.get('nf2', '') for r in tab[tA]]
        ok0 = not any(str(v).strip() not in ('', '0', '0.0') for v in nf2a)
        print('  T2-0 正对照（%s 的 nf2 应恒 0）：%s' % (tA, '✅ PASS' if ok0 else '⛔'))
    if tB in tab:
        nf2b = [r.get('nf2', '') for r in tab[tB]]
        ok1 = any(str(v).strip() not in ('', '0', '0.0') for v in nf2b)
        print('  T2-1（%s 的 nf2 应 ≥1）：%s' % (tB, '✅ **PASS**' if ok1 else '⛔ FAIL'))
    for t, rows in tab.items():
        bt = {str(r.get('box_touch')) for r in rows}
        print('  T2-3 %s 的 box_touch 取值集合 = %s ⇒ %s'
              % (t, sorted(bt), '✅' if bt == {'0'} else '⚠ 撞过盒'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
