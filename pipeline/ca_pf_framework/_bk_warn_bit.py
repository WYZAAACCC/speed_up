#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_warn_bit.py —— 核验：**"归档路径"提示是纯打印，没有改任何数**。

做法：拿归档最简命令跑 **20 步**（与 `eng12` 的前 20 步同参数、同步长），
把它 series.csv 里 `step ≤ 20` 的行与 `eng12` 的同 step 行**逐字段比**。
二者应逐位相同 —— 否则说明那条提示动到了行为（它不该动）。

⚠ 只比 `eng12` 有的列（新增列如 `cfl_used`/`f3_pairs_pos` 不参与）。
"""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'wall_s'}


def load(tag, root):
    p = os.path.join(_HERE, root, tag, 'series.csv')
    return list(csv.DictReader(open(p)))


def main():
    a = load('eng_eng12', '_exp/_bk_eng')
    b = load('dry_defw', '_exp/_bk_eng')
    amap = {x['step']: x for x in a}
    bad, n = [], 0
    for y in b:
        x = amap.get(y['step'])
        if x is None:
            bad.append((y['step'], '（eng12 里没有这个 step）', '', ''))
            continue
        n += 1
        for k in x:
            if k in SKIP:
                continue
            if x[k] != y[k]:
                bad.append((y['step'], k, x[k], y[k]))
    extra = [k for k in b[0] if k not in a[0]]
    print('比对行数 = %d（defw 的全部行都应在 eng12 里找得到）' % n)
    print('逐字段差异 = %d' % len(bad))
    for t in bad[:10]:
        print('   step=%s %s: eng12=%r defw=%r' % t)
    print('未参与比较的新列：%s' % (extra or '（无）'))
    print('⇒ %s' % ('**提示是纯打印，数值逐位未变**' if not bad
                    else '**有差异 ⇒ 提示动到了行为，必须查**'))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
