#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ledger.py --- ★★★★★ 复核 goal 判据①：**16 个算子是不是**逐个**有结论**

## 判据（goal 逐字）
> 「≥5% 的 16 个算子逐个有结论：要么"拿到实测收益"（配对中位 + 区间），
>   要么"给出可复现的否定结论"（试过的路线 + 实测数）。**不允许留"未测"**」

## 怎么算数
* **有结论** = 状态列里出现**提速比**（数字 + ×）**或**明确写"否定/逐位相同/口径"；
* **未测** = 状态列只有 🚧 / ⬜ / 空 ⇒ **不算**（但**要区分**"未测"与"已测但结论是否定"）。
"""
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else 'OPOPT_LEDGER.md'

# 「有结论」的证据模式
HIT = [
    (r'\d+\.\d+\s*×', '有提速比（×）'),
    (r'否定|作废|判死|无效|更慢|不可行', '明确的否定结论'),
    (r'逐位', '逐位相同（口径结论）'),
    (r'未确立|未复现', '口径结论（速度未确立）'),
    (r'噪声地板', '口径结论（在噪声下）'),
]
# 「未测」的证据
MISS = [r'🚧', r'⬜', r'未做', r'待做', r'尚未']


def main():
    rows = []
    for line in open(PATH, encoding='utf-8', errors='replace'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 4:
            continue
        tag = cells[0]
        if not re.match(r'^\**\s*[A-Z]\d+', tag):
            continue
        rows.append((re.sub(r'\*', '', tag).strip(), cells[-1] if len(cells) >= 5 else ''))
    print('=' * 100)
    print('goal 判据① 复核：`%s` 里的算子条目' % PATH)
    print('=' * 100)
    n_ok = n_miss = 0
    for tag, status in rows:
        hit = [d for p, d in HIT if re.search(p, status)]
        miss = [p for p in MISS if re.search(p, status)]
        if hit and not (miss and not hit):
            n_ok += 1
            print('  ✅ %-6s %s' % (tag, ' / '.join(sorted(set(hit))[:2])))
        else:
            n_miss += 1
            print('  ⚠ %-6s **未见结论证据**；状态片段：%s' % (tag, status[:70]))
    print()
    print('  **有结论 %d 条 / 需复核 %d 条**（总条目 %d）' % (n_ok, n_miss, len(rows)))
    print()
    print('  ★ 若"需复核"里有的其实是**已测但结论否定**（状态列没写数字），要人工看一遍。')
    print('=' * 100)


if __name__ == '__main__':
    main()
