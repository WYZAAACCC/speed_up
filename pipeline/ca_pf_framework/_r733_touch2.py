#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r733_touch2.py <root> [tag ...] —— 直接读 `series.csv` 的 `box_touch`（不依赖目录列举的成功与否）。

与 `_r720_touch.py` 的区别：本脚本**先打印目录列举结果**，便于区分子「没有目录」与「目录列举失败」。
"""
import csv
import os
import sys


def main():
    root = sys.argv[1]
    tags = sys.argv[2:]
    print('root = %s' % root)
    print('  exists = %s' % os.path.isdir(root))
    try:
        allnames = os.listdir(root)
        print('  listdir 返回 %d 个条目' % len(allnames))
        dry = sorted(n for n in allnames if n.startswith('dry_'))
        print('  其中 dry_* = %d 个' % len(dry))
    except OSError as e:
        print('  ⛔ listdir 失败: %s' % e)
        return 1
    if tags:
        dry = ['dry_%s' % t for t in tags]
    print()
    print('  %-30s %8s %10s %12s' % ('tag', '最后step', '首撞盒', '撞盒前最后步'))
    for d in dry:
        p = os.path.join(root, d, 'series.csv')
        if not os.path.isfile(p):
            continue
        rows = []
        with open(p, newline='') as f:
            for r in csv.DictReader(f):
                try:
                    rows.append((int(r['step']), int(float(r.get('box_touch') or 0))))
                except (ValueError, TypeError, KeyError):
                    pass
        if not rows:
            continue
        last = rows[-1][0]
        first = next((s for s, b in rows if b == 1), None)
        safe = max((s for s, b in rows if b == 0), default=None)
        print('  %-30s %8d %10s %12s%s'
              % (d[4:][:30], last, first if first is not None else '从未',
                 safe if safe is not None else '无', '  ⚠' if first else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
