#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_fixdoc2.py —— 参数条数从 43 增到 46 之后，同步文档里的三处计数。"""
import io
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(_HERE, 'BLOCK_PARAM_CLOSURE.md')
SUBS = [
    ('参数总表（由代码生成，43 条）', '参数总表（由代码生成，46 条）'),
    ('完整 43 条见', '完整 46 条见'),
    ('43 条参数每一条都有', '46 条参数每一条都有'),
    ('**能。** 43 个参数里', '**能。** 46 个参数里'),
    ('**[推] 纯推导 6 条**', '**[推] 纯推导 7 条**'),
    ('**[标] 仍需标定但已收成单一可测常数 10 条**',
     '**[标] 仍需标定但已收成单一可测常数 11 条**'),
    ('**[数] 数值/建模选择（不是物理量、不需要标定）14 条**',
     '**[数] 数值/建模选择（不是物理量、不需要标定）15 条**'),
    ('| **[推]** | 6 |', '| **[推]** | 7 |'),
    ('| **[标]** | 10 |', '| **[标]** | 11 |'),
    ('| **[数]** | 14 |', '| **[数]** | 15 |'),
]


def main():
    t = io.open(P, encoding='utf-8').read()
    n = 0
    for a, b in SUBS:
        if a in t and a != b:
            t = t.replace(a, b)
            print('改了  %-52s → %s' % (a[:52], b[:40]))
            n += 1
    io.open(P, 'w', encoding='utf-8').write(t)
    print('共改 %d 处' % n)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
