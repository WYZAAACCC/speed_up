#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r302_collect.py —— 采集**当前真实**的统计量，供更新 `AUDIT_SUMMARY_R76.md` 的表头与 §0/§1。

⚠ 原则：**只写能核实的数**。每个数都注明来源（哪个 grep/哪个节）。
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
DOC = os.path.join(HERE, 'AUDIT_SUMMARY_R76.md')


def main():
    led = io.open(LED, encoding='utf-8').read()
    doc = io.open(DOC, encoding='utf-8').read()
    lines = led.count('\n') + 1
    secs = re.findall(r'^## (§\d+)', led, re.M)
    nums = [int(s[1:]) for s in secs]
    print('=' * 100)
    print('_r302 —— 当前真实统计（供更新摘要表头）')
    print('=' * 100)
    print('  台账：%d 行；节数 %d；节号范围 §%d … §%d'
          % (lines, len(secs), min(nums), max(nums)))
    print('  摘要：%d 行' % (doc.count('\n') + 1))
    # 缺陷编号
    pids = sorted({int(m) for m in re.findall(r'P1-(\d+)', led)})
    print('  台账里出现过的缺陷编号：P1-%d … P1-%d，共 **%d** 个不同编号'
          % (min(pids), max(pids), len(pids)))
    print('     编号列表：%s' % ', '.join('P1-%d' % p for p in pids))
    # 撤回指针
    ptr = re.findall(r'本节已被\s*`(§\d+)`', led)
    print('  "本节已被 §x 撤回/更正" 就地指针：**%d** 个（%s）'
          % (len(ptr), ','.join(sorted(set(ptr), key=lambda s: int(s[1:])))))
    # 本会话新增的节（§129 起）
    new = [s for s in secs if int(s[1:]) >= 129]
    print('  本会话新增节（§129 起）：**%d** 个（§129 … §%d）' % (len(new), max(nums)))
    # 硬规则
    # 硬规则（只统计"硬规则 ⓝ"出现次数，不做字符集运算）
    rules = re.findall(r'硬规则\s*([③-⑳㉑-㉜])', led)
    if rules:
        from collections import Counter
        c = Counter(rules)
        print('  "硬规则" 提及：共 %d 处，涉及 %d 个不同序号：%s'
              % (len(rules), len(c), ''.join(sorted(c))))
    else:
        print('  （未匹配到"硬规则 ⓝ"）')
    print()
    print('  摘要当前表头（前 8 行）：')
    for i, L in enumerate(doc.split('\n')[:8]):
        print('     %d: %s' % (i + 1, L))
    print()
    print('  ⚠ 判断：表头若仍写 "§87–§126，7882 行" ⇒ **已过期**，需更新。')
    stale = ('7882' in doc.split('\n---')[0]) or ('§126' in doc.split('\n---')[0])
    print('     ⇒ 表头过期？ **%s**' % ('是' if stale else '否'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
