#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_axes.py —— **只读**：从 `series.csv` 抽**每个 tag** 的
`box_touch` 时间线 + 指定的几列，用于**在安全区间内重取读数**。

## 为什么需要它
`box_touch=1` ⇒ 板条长出周期盒 ⇒ 之后**形状/跨度/平整度**读数全部被盒约束。
`R720 §1` 已实测：本轮的 `B2P_q0`(225) / `CLIell`(175) / `CLIbig`(**100**) /
`Mlo3`(150) / `Mhi12`(325) **全都撞过盒**，只有 `B2P_pre` **从未**。
⇒ 先前"同配置矩阵 @175"里凡"撞盒步 < 175"的臂，其读数**不可用**。

## 用法
    python3 _r720_axes.py <root> <tag> [<tag> ...] --cols nslab_n,nf3_col,Vt
    python3 _r720_axes.py <root> --safe-only --cols nslab_n,nf3_col
"""
import csv
import os
import sys


def read_rows(path):
    with open(path, newline='') as f:
        rd = csv.DictReader(f)
        return rd.fieldnames or [], list(rd)


def main():
    roots, tags, cols = [], [], []
    args = sys.argv[1:]
    i = 0
    root0 = None
    while i < len(args):
        if args[i] == '--cols':
            cols = args[i + 1].split(',')
            i += 2
            continue
        if root0 is None:
            root0 = args[i]
        else:
            tags.append(args[i])
        i += 1
    roots = [root0]
    if not cols:
        cols = ['nslab_n', 'nf3_col', 'Vt']

    print('=' * 100)
    print('按 `box_touch` 截断后的读数（root=%s）' % root0)
    print('=' * 100)
    for t in tags:
        p = os.path.join(root0, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('【%s】⚠ 无 series.csv' % t)
            continue
        hdr, rows = read_rows(p)
        if 'box_touch' not in hdr:
            print('【%s】⚠ 无 box_touch 列' % t)
            continue
        safe = []
        for r in rows:
            try:
                if int(float(r['box_touch'])) == 1:
                    break
            except (ValueError, TypeError):
                pass
            safe.append(r)
        first_touch = next((r['step'] for r in rows
                            if str(r.get('box_touch', '')).strip() in ('1', '1.0')), None)
        print('\n【%s】首次撞盒 step = %s ；安全行数 = %d'
              % (t, first_touch if first_touch else '从未', len(safe)))
        if not safe:
            continue
        head = ['step'] + cols
        print('   ' + ' '.join('%-13s' % c for c in head))
        for r in safe:
            vals = []
            for c in head:
                v = r.get(c, '')
                try:
                    fv = float(v)
                    vals.append('%-13.6g' % fv)
                except (ValueError, TypeError):
                    vals.append('%-13s' % str(v)[:13])
            print('   ' + ' '.join(vals))
    return 0


if __name__ == '__main__':
    sys.exit(main())
