#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_sixteen.py --- ★★★★★★ **goal 判据① 的核心复核**：≥5% 墙钟的算子**到底是哪 16 个**、各自有没有结论

## 为什么必须做
**`OPOPT_LEDGER.md` 有 31 条（A1–A31），其中多条写着「未动」「未做」** ⇒ **表面上像"留了未测"**。
**但 goal 要求的是**≥5% 墙钟占比的那 16 个**** ⇒ **只有那 16 个必须逐个有结论**。
**⇒ 本脚本按「实测代价」列筛出 ≥5% 的条目，再逐条看状态列有没有结论。**

## 口径（**先写死**）
* **代价**：从「实测代价」列抽第一个百分数（`xx.xx%`）；
* **≥5%** ⇒ **进"必须"名单**；
* **结论证据**：状态列里有 **`×`（提速比）/ 否定 / 逐位 / 未确立 / 噪声** 之一；
* **顶层容器**（状态写着"顶层容器"/"见 A"/"同上"）⇒ **不算独立条目**（它的子项才是）。
"""
import re
import sys

PATH = sys.argv[1] if len(sys.argv) > 1 else 'OPOPT_LEDGER.md'
THRESH = 5.0
HIT = [r'\d+\.\d+\s*×', r'否定|作废|判死|无效|更慢|不可行', r'逐位',
       r'未确立|未复现', r'噪声地板', r'不值得动']
CONTAINER = [r'顶层容器', r'^见 A', r'同上', r'三个子项见']


def main():
    rows = []
    for line in open(PATH, encoding='utf-8', errors='replace'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) < 5:
            continue
        tag = re.sub(r'\*', '', cells[0]).strip()
        if not re.match(r'^[A-Z]\d+$', tag):
            continue
        cost_cell, status = cells[2], cells[4]
        nums = re.findall(r'(\d+\.?\d*)\s*%', cost_cell)
        cost = max((float(x) for x in nums), default=None)
        rows.append((tag, cost, cost_cell[:44], status))

    print('=' * 104)
    print('goal 判据①：**≥%.0f%% 墙钟**的算子逐条复核（源：`%s`）' % (THRESH, PATH))
    print('=' * 104)
    must, other = [], []
    for r in rows:
        (must if (r[1] is not None and r[1] >= THRESH) else other).append(r)

    def show(lst, title):
        print()
        print('── %s（%d 条）──' % (title, len(lst)))
        print('  %-6s %-9s %-30s %s' % ('条目', '代价%', '状态片段', '结论？'))
        print('  ' + '-' * 98)
        ok = bad = cont = 0
        for tag, cost, cc, status in lst:
            iscont = any(re.search(p, status) for p in CONTAINER)
            hit = any(re.search(p, status) for p in HIT)
            if iscont:
                verdict, cont = '（顶层容器，不计）', cont + 1
            elif hit:
                verdict, ok = '✅ 有结论', ok + 1
            else:
                verdict, bad = '⚠ **未见结论证据**', bad + 1
            print('  %-6s %-9s %-30s %s' % (tag, ('%.2f' % cost) if cost is not None else '—',
                                             status[:30], verdict))
        print('  ⇒ **有结论 %d / 未见 %d / 容器 %d**' % (ok, bad, cont))
        return ok, bad, cont

    m = show(must, '★ **≥5% 墙钟**（goal 要求逐个有结论的这批）')
    show(other, '<5% 或代价未列（goal **不强制**逐个有结论）')
    print()
    print('=' * 104)
    print('  ★ 判读：**"≥5%" 那一批若"未见结论"= 0 ⇒ goal 判据① 成立**')
    print('         若 > 0 ⇒ **必须补**（goal 逐字：「不允许留"未测"」）')
    print('=' * 104)


if __name__ == '__main__':
    main()
