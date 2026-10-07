#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r304_append160.py —— 追加 `§160`：**别把"会增长的计数"写进引用它的文档**。"""
from __future__ import annotations

import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LED = os.path.join(HERE, 'R30_AUDIT_LEDGER.md')
MARK = '## §160'

SEC = r"""
---

## §160（R304）**别把"会增长的计数"写进引用它的文档**（`§159` 的即时自我更正）

### §160.1 事情经过

`§159` 我刚把摘要表头改成 `§0–§158，10554 行`。
**紧接着 `§159` 自己就把台账从 10554 行写到 10596 行** ⇒ **表头当场又过期了。**

**⇒ 这是一类**结构性**问题，不是一次疏忽**：
`AUDIT_SUMMARY_R76.md` 是**引用**台账的索引文档，而台账**每写一节就变长**。
**只要在摘要里写死台账的行数/节号，它必然永远落后一轮。**

### §160.2 修法与规则

**修法**：摘要表头改成**与计数无关**的表述 ——
> `R30_AUDIT_LEDGER.md`（**§0 起，节号与行数持续增长**；本表写就时为 §0–§159 / 约 10600 行）
> ⚠ **行数/节号一律以台账实际为准**（本文件不追着改数字）。

**⇒ 硬规则 ㉝（本轮新增）**：
**引用型文档（索引/摘要）**不得**写死被引用文档的"长度类"数字**（行数、节数、总条目数）；
要么写成**区间 + 生成时刻**（`写就时 §0–§159`），要么**只写节号锚点**。
**判据**：写完自查一句 —— **"我这一改，会不会让刚才写的那个数立刻过期？"**

### §160.3 记账

* ✅ 摘要表头已改为**计数无关**；`§0 一页速览` 同样不再写台账行数。
* ⚠ **保留**"写就时为 §0–§159 / 约 10600 行"作为**时间戳**（有价值：能判断本表的新旧），
  但**明确声明以台账实际为准**。
* ⏳ 在跑：`_r280` 60/400、`_r253` 280/400、`_r240`；文档：台账 10596 行 / 摘要 930 行 / 制表符 0。
"""


def main():
    with io.open(LED, 'r', encoding='utf-8') as f:
        txt = f.read()
    n0 = txt.count('\n') + 1
    if MARK in txt:
        print('⚠ 已有 `%s` ⇒ 不重复追加（当前 %d 行）' % (MARK, n0))
        return 0
    assert txt.endswith('\n'), '台账末尾不是换行'
    assert '\t' not in SEC, '正文里有制表符'
    with io.open(LED, 'a', encoding='utf-8', newline='') as f:
        f.write(SEC)
    with io.open(LED, 'r', encoding='utf-8') as f:
        t2 = f.read()
    n1 = t2.count('\n') + 1
    print('✅ 台账：%d 行 → **%d 行**（+%d）；制表符 = %d'
          % (n0, n1, n1 - n0, t2.count('\t')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
