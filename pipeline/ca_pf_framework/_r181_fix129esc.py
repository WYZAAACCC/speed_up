#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r181_fix129esc.py —— 修 `§129` 里被 Python 转义吃掉的制表符。

**根因**：`_r180_append129.py` 的 `SEC` 是**普通字符串**（非 raw），
里面写了 `\\Delta\\theta` ⇒ 其中 **`\\t` 被解释成制表符** ⇒ 台账里变成
`\\Delta<TAB>heta`。同一行的 `\\(` / `\\)` 也退化成了 `\\(` / `\\)`。

**教训**：往 Markdown 里写 LaTeX 时用 **raw 字符串**（`r\"\"\"…\"\"\"`）
或直接用本仓库既有的 `@@…@@` 记号。

**做法**：按行定位（含"相邻同变体对"的那一行），**整行重写**，不碰别处。
"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')

ANCHOR = '相邻同变体对'
NEWLINE = ('| M | \u0394\u03b8[\u00b0] | \u76f8\u90bb\u540c\u53d8\u4f53\u5bf9 '
           '\u03b3 = \u03b3_RS(\u0394\u03b8) | /\u03b3\u2080(=0.25) | '
           '\u9996\u672b\u5bf9 \u03b8 | \u9996\u672b\u5bf9 \u03b3 | '
           '/\u03b3\u2080 |')


def main():
    with io.open(LED, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
    n0 = len(lines)
    hits = [i for i, L in enumerate(lines) if ANCHOR in L]
    print('命中行号（0 基）= %s' % hits)
    if len(hits) != 1:
        print('⚠ 命中数不为 1 ⇒ 拒绝修改')
        return 1
    i = hits[0]
    print('修改前：%r' % lines[i][:130])
    assert lines[i].startswith('| M |'), '命中行不是那张表的表头，拒绝改'
    lines[i] = NEWLINE
    print('修改后：%r' % lines[i][:130])
    with io.open(LED, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(lines))
    with io.open(LED, 'r', encoding='utf-8') as f:
        t = f.read()
    n1 = t.count('\n') + 1
    print('行数 %d → %d（应不变）' % (n0, n1))
    assert n0 == n1, '行数变了 ⇒ 误伤'
    print('全文制表符个数 = %d（原先应为 1，即那一格）' % t.count('\t'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
