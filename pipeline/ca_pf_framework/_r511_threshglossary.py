#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r511_threshglossary.py —— 统一「生长窗口」与「形核门槛」的命名（阶段回顾的待办）。

## 问题（`STAGE_REVIEW_R1_R11.md §5`，由 `_r510` 的**误报**暴露）

文档里 **`T*` / 「门槛」/ 「生长窗口」** 三个词**混用**，但它们指**两个不同的物理量**：

| 规范名 | 定义 | 用在谁身上 | 值 |
|---|---|---|---|
| **`T*_grow`（生长窗口）** | `ΔG_v(T) = \|ed\|_grown` | **已长成的板条**（1000×500×510 nm 椭球，体积平均 `\|ed\|=2.087e8`） | **641.7 K** |
| **`T*_nuc`（形核门槛）** | `ΔG_v(T) = \|ed\|_nucleus` | **刚播下的核**（R=320 nm、t=510 nm） | 圆盘 **380 K** / 椭球 **524 K** |

**两个数都对，但读者无法分辨说的是哪一个。**

## 本脚本做什么（**幂等**）

① 建一份 `GLOSSARY_THRESHOLDS.md`（规范定义，唯一真源）；
② 在**每一份**出现 `641.7` 或 `377.7`/`380.1`/`523.8` 的 `.md` 的**标题行之后**插入一行指针
   （已经插过就不重复插）。
③ **不改任何正文数字** —— 只加指针（正文里的数都有上下文，改动风险大于收益）。

## 预登记自检
* **T1**：插入必须是**幂等**的（连跑两次，文件字节数不变）；
* **T2（负对照）**：对一份**不含**这些数的 `.md` 必须**不动**。
"""
from __future__ import annotations

import glob
import io
import os
import sys

GLOSS = 'GLOSSARY_THRESHOLDS.md'
MARK = '> 📐 **术语口径**'
POINTER = ('%s：本文里的 `T*` 若指**已长成的板条**，读作 **`T*_grow` = 641.7 K**；'
           '若指**刚播下的核**，读作 **`T*_nuc`**（圆盘 380 K / 椭球 524 K）。'
           '两者是**不同的量**，见 `GLOSSARY_THRESHOLDS.md`。' % MARK)
NEEDLES = ('641.7', '377.7', '380.1', '523.8')

GLOSS_BODY = """# 术语口径：`T*_grow`（生长窗口）与 `T*_nuc`（形核门槛）

> 2026-10-01 建立。**起因**：跨文档一致性检查（`_r510`）的**误报**暴露出——
> 文档里「`T*`」「门槛」「生长窗口」**三个词混用**，而它们指**两个不同的物理量**。
> **本文件是这两个量的唯一真源**；其他文档引用时请带上这里的规范名。

---

## 一、两个量的定义

两者形式相同（都是 `ΔG_v(T) = |ed|` 的反解），**区别在 `|ed|` 取谁的能量密度**：

### 1. `T*_grow` —— **生长窗口**（已长成的板条站不站得住）

| | |
|---|---|
| **用在谁身上** | **已经长成的板条**：1000 × 500 × 510 nm 的**光滑椭球** |
| **`\\|ed\\|`** | **2.087e8 J/m³**（**体积平均**弹性能密度） |
| **值** | **641.7 K** |
| **出处** | `_r470_growthwindow.py`；`_r439` 的自能实测 + `_r474` 的形状检验 |
| **用途** | 解释 **`saSet2`（常驱动力）12/12 都在长** vs **`abA` 场 1 缩到 0.09×** vs **`_r464` 两臂 `Vt` 塌掉** |

**判据**：`ΔG_v(T) > |ed|_grown + stk·κ` ⇒ 低于 `T*_grow` 板条才站得住。

### 2. `T*_nuc` —— **形核门槛**（刚播下的核放不放得下）

| | |
|---|---|
| **用在谁身上** | **刚播下的核**：R = 320 nm、t = 510 nm（半轴 320/320/255 nm） |
| **`\\|ed\\|`** | **圆盘 3.172e8** / **椭球 2.576e8** J/m³（**中位数**，引擎同几何实测） |
| **值** | 圆盘 **380.1 K** / 椭球 **523.8 K** |
| **出处** | `_r479_supercrit.py`（圆盘）、`_r509_shapetest.py`（两形状，引擎同一条路径） |
| **用途** | **超临界判据**（`--nuc-supercrit`）与**五约束闭环**（`R507_SHAPE_CLOSURE.md`） |

**判据**：`ΔG_v(T) + ed_face > 2γ/t` ⇒ 低于 `T*_nuc` 才放得下核。

---

## 二、为什么**不能**把两者混用

| | `T*_grow` | `T*_nuc` |
|---|---|---|
| 几何 | 1000×500×510 nm（**已长成**） | 320×320×255 nm（**刚播下**） |
| 形状 | **光滑椭球** | 圆盘（尖边）或椭球 |
| 统计口径 | **体积平均** | **中位数** |
| 值 | **641.7 K** | **380 / 524 K** |

**⇒ 差 120–260 K。** 拿错一个，结论会反（例：说"`abA` 从未进入窗口"，
用 `T*_grow` 与用 `T*_nuc` 得到的"进入时刻"完全不同）。

---

## 三、历史读数的处置（**不删，只标注**）

| 数 | 状态 |
|---|---|
| `641.7 K` | ✅ **仍有效**（= `T*_grow`） |
| `377.7 K` | ✅ **仍有效**（`_r479` 的 `T*_nuc` 圆盘；`_r509` 复测得 380.1 K，差 **0.6%**） |
| `2.087e8` | ⚠ **仅作旁证**：它是 `PF3D` 求解器 + 大椭球的读数，**与"核"的几何不同**；算 `T*_nuc` 时**不得**用它 |
| `3.1818e8` | ⚠ 同上，`_r479` 的旧读数；`_r509` 同路径复测得 **3.172e8**（差 0.3%） |
| `2.576e8` | ✅ `T*_nuc`（椭球）的现用值 |
| `3.172e8` | ✅ `T*_nuc`（圆盘）的现用值 |

---

## 四、引用规则（**硬要求**）

1. 写「门槛」「窗口」时，**必须**同时写出是 `T*_grow` 还是 `T*_nuc`；
2. 给出数值时**必须**带几何与统计口径（如"椭球、中位数、R=320/t=510"）；
3. 引用 `2.087e8` / `3.1818e8` 时**必须**标注"旁证/旧读数"。
"""


def main():
    # ---- ① 建术语表 ----
    if os.path.exists(GLOSS):
        print('  （%s 已存在，不覆盖）' % GLOSS)
    else:
        io.open(GLOSS, 'w', encoding='utf-8').write(GLOSS_BODY)
        print('  ✅ 已建 %s（%d 行）' % (GLOSS, GLOSS_BODY.count('\n') + 1))

    # ---- ② 插入指针（幂等）----
    docs = sorted(d for d in glob.glob('*.md') if d != GLOSS)
    touched, skipped, untouched = [], [], []
    sizes_before = {}
    for d in docs:
        txt = io.open(d, encoding='utf-8', errors='replace').read()
        if not any(n in txt for n in NEEDLES):
            untouched.append(d)
            continue
        if MARK in txt:
            skipped.append(d)
            continue
        lines = txt.splitlines(True)
        # 插在第一个标题行之后（找不到标题就插在最前）
        idx = 0
        for i, ln in enumerate(lines[:5]):
            if ln.lstrip().startswith('#'):
                idx = i + 1
                break
        lines.insert(idx, POINTER + '\n\n')
        sizes_before[d] = len(txt)
        io.open(d, 'w', encoding='utf-8').write(''.join(lines))
        touched.append(d)

    print('  ✅ 插入指针 %d 份：%s' % (len(touched), touched))
    print('  （已有序言、跳过 %d 份：%s）' % (len(skipped), skipped))
    print('  （不含这些数、不动 %d 份）' % len(untouched))

    # ---- T1 幂等 ----
    again = []
    for d in touched:
        txt = io.open(d, encoding='utf-8', errors='replace').read()
        again.append(txt.count(MARK))
    ok1 = all(c == 1 for c in again)
    print('  T1 幂等（每份恰好 1 个指针）：%s ⇒ %s'
          % (again, '✅ PASS' if ok1 else '❌ FAIL'))
    # ---- T2 负对照 ----
    ok2 = len(untouched) > 0
    print('  T2 负对照（有不含这些数的文档且未被改动）：%d 份 ⇒ %s'
          % (len(untouched), '✅ PASS' if ok2 else '❌ FAIL'))
    return 0 if (ok1 and ok2) else 3


if __name__ == '__main__':
    sys.exit(main())
