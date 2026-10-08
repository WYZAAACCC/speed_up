#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r720_touch.py <root> <tag> [tag ...] —— 打印每臂的 `box_touch` 时间线（**只读**）。

## 为什么需要它
`box_touch=1` ⇒ 板条已长到**周期盒边界** ⇒ 之后的一切**形状/跨度**读数都被盒约束，
**不可作为"单个板条"的证据**（本仓老教训：`R641 §7`、`R645 §9.1`）。
⇒ **任何跨臂形状比较，必须先确认各臂在**同一步**都 `box_touch=0`。**

## 用法
    python3 _r720_touch.py _exp/_bk_block B2P_q0 B2P_pre B40 L1 Mlo3 Mhi12
    python3 _r720_touch.py --list _exp/_bk_block        # 列出全部臂及其首次撞盒步
"""
import csv
import os
import sys


def timeline(path):
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            try:
                rows.append((int(r['step']), int(float(r['box_touch']))))
            except (KeyError, ValueError, TypeError):
                pass
    return rows


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    listing = (a[0] == '--list')
    root = a[1] if listing else a[0]
    tags = None if listing else a[1:]

    if tags is None:
        tags = []
        for d in sorted(os.listdir(root)):
            if d.startswith('dry_') and os.path.isfile(os.path.join(root, d, 'series.csv')):
                tags.append(d[4:])

    print('=' * 96)
    print('`box_touch` 时间线（root=%s）—— 判据：跨臂比较必须在 step ≤ 各臂首次撞盒步' % root)
    print('=' * 96)
    print('  %-30s %8s %10s %12s' % ('tag', '最后step', '首撞盒step', '撞盒前最后step'))
    for t in tags:
        p = os.path.join(root, 'dry_%s' % t, 'series.csv')
        if not os.path.isfile(p):
            print('  %-30s  ⚠ 无 series.csv' % t)
            continue
        rows = timeline(p)
        if not rows:
            print('  %-30s  ⚠ 无 box_touch 列' % t)
            continue
        last = rows[-1][0]
        first = next((s for s, b in rows if b == 1), None)
        safe = max((s for s, b in rows if b == 0), default=None)
        print('  %-30s %8d %10s %12s%s'
              % (t[:30], last, first if first is not None else '从未',
                 safe if safe is not None else '从未为 0',
                 '' if first is None else '  ⚠ 撞过盒'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
