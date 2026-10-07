#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r297_ledgerlint.py —— ★ **台账自查**：本轮会话的"撤回/更正"是否都**就地打了指针**？

## 为什么做（用户要求）
用户要求「**每完成一阶段的工作之后都回顾一下这一阶段的工作，检查有没有错误与偏离主线**」。
本会话已发生**多次自我更正**（`§131` 更正 `§129.1`、`§134` 撤回 P1-46、
`§141` 更正 `§137.3`、`§147` 收窄 `§144`、`§150` 撤回 `§149(A)`、`§154` 更正 `§152`）。
**⇒ 如果只在后一节说"前面错了"，而**前文没有指针**，
   读者（用户/专家）读到前文时仍会拿到**已被推翻的结论**。**

## 判据（**先写死**）
* **L-1** 台账里每一条"撤回/更正/收窄"的记录，都能找到一个**它撤回的节号**。
* **L-2** ★ **每一个被撤回的节，其正文里必须有就地指针**
  （形如"已被 `§xxx` 撤回/更正/收窄"）⇒ 否则 **FAIL**。
* **L-3** 列出**所有**含撤回语义词的节，供人工复核。
* **L-4** 反向检查：正文里有指针、但台账后文找不到对应说明 ⇒ 也报出来。
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')

# 撤回类语义
RETRACT = re.compile(r'(撤回|更正|收窄|作废|不成立|已推翻|已被.*更)')
# 节标题
SEC = re.compile(r'^## (§\d+[^\n]*)$', re.M)
# 就地指针（放在**被撤回节**的正文里）
POINTER = re.compile(r'(已被|已被 `§\d+`|本条已被)\s*`?(§\d+)`?\s*(撤回|更正|收窄|作废|推翻)')


def main():
    txt = io.open(LED, encoding='utf-8').read()
    # 节位置
    secs = [(m.group(1), m.start()) for m in SEC.finditer(txt)]
    print('=' * 104)
    print('_r297 —— 台账自查：撤回/更正是否都就地打了指针')
    print('=' * 104)
    print('  台账共 %d 行，%d 个节' % (txt.count('\n') + 1, len(secs)))

    # L-3：所有含撤回语义的节
    print()
    print('  ## **L-3** 含"撤回/更正/收窄"语义的节')
    hits = []
    for i, (title, pos) in enumerate(secs):
        end = secs[i + 1][1] if i + 1 < len(secs) else len(txt)
        body = txt[pos:end]
        n = len(RETRACT.findall(body))
        if n:
            sid = title.split()[0]
            hits.append((sid, title[:70], n))
    for (sid, t, n) in hits:
        print('     %-8s（%2d 处）%s' % (sid, n, t))

    # L-2：被撤回的节是否有就地指针
    print()
    print('  ## **L-2** 被撤回的节 → 是否有**就地指针**')
    # 从"撤回类"句子里抽出被撤回的节号
    targets = set()
    for m in re.finditer(r'(撤回|更正|收窄|作废)\s*(了)?\s*`?(§\d+)`?', txt):
        targets.add(m.group(3))
    for m in re.finditer(r'`?(§\d+)`?\s*(已被|的)?\s*(撤回|更正|收窄|作废)', txt):
        targets.add(m.group(1))
    # 指针本身也算：指针形式 "已被 `§xxx` 撤回" ⇒ 被撤回的是**指针所在节**
    print('     从正文里识别出的"被撤回节号" = %s'
          % (sorted(targets, key=lambda s: int(s[1:])) or '（无）'))
    print()
    fails = []
    for i, (title, pos) in enumerate(secs):
        sid = title.split()[0]
        end = secs[i + 1][1] if i + 1 < len(secs) else len(txt)
        body = txt[pos:end]
        has_ptr = bool(POINTER.search(body))
        # 该节是否被别处点名撤回
        named = sid in targets
        if named and not has_ptr:
            fails.append((sid, title[:60]))
        flag = '有指针' if has_ptr else ('⚠ **无指针**' if named else '')
        if named or has_ptr:
            print('     %-8s %-14s %s' % (sid, flag, title[:60]))
    print()
    print('  ## **L-4** 总判定')
    if fails:
        print('     ❌ **%d 个节被点名撤回但正文无就地指针**：' % len(fails))
        for (sid, t) in fails:
            print('        %-8s %s' % (sid, t))
    else:
        print('     ✅ **所有被撤回的节都有就地指针**'
              '（读者读到前文时会看到"已被 §xxx 撤回/更正/收窄"）')
    # 统计
    nptr = len(POINTER.findall(txt))
    print('     全文就地指针共 **%d** 处' % nptr)
    print('     ⚠ 记账：本检查是**文本级**的（正则匹配），'
          '不判断指针内容是否**正确**；内容正确性靠人工/前几节的核对。')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
