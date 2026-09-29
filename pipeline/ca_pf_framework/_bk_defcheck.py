#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_defcheck.py —— 核验：**最简命令行**（默认路径）与已验的 `eng12` 是否逐位一致。

忽略 `wall_s`（墙钟，必然不同）。用法：
    python3 _bk_defcheck.py [tag]          # tag 默认 def1（R28 归档的那次）

⚠ 比较口径：只遍历 **`eng12` 那一行的键** ⇒ 后来新增的列（如 R29 的 `cfl_used`）
  **不参与比较、既不报差异也不被验证**。这一条必须写出来，否则会被读成
  "所有列都逐位相同"。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'wall_s'}


def load(tag, root):
    p = os.path.join(HERE, root, tag, 'series.csv')
    return list(csv.DictReader(open(p)))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'def1'
    a = load('eng_eng12', '_exp/_bk_eng')
    b = load('dry_%s' % tag, '_exp/_bk_eng')
    print('行数: eng12=%d  %s=%d' % (len(a), tag, len(b)))
    extra = [k for k in b[0] if k not in a[0]]
    bad = []
    for i, (x, y) in enumerate(zip(a, b)):
        for k in x:
            if k in SKIP:
                continue
            if x[k] != y[k]:
                bad.append((i, k, x[k], y[k]))
    print('逐位比较（忽略 wall_s；**只比 eng12 有的列**）：差异字段数 = %d' % len(bad))
    for t in bad[:12]:
        print('   step=%s  %s: eng12=%r  %s=%r'
              % (a[t[0]]['step'], t[1], t[2], tag, t[3]))
    print('⚠ 未参与比较的新列：%s' % (extra or '（无）'))
    print('⇒ %s' % ('**共有列逐位一致**' if not bad else '**有差异**（见上）'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
