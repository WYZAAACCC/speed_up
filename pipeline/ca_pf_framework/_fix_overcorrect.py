#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_fix_overcorrect.py --- **撤销我自己的过度纠正**：Shuai 2026 给的**确实是"厚"**

背景（Round 139 第三轮 —— 纠错的纠错）
--------------------------------------
上一轮（`_fix_9to1.py` / 提交 `3fab9673`）我据 Wang 2026 的
"average **length and width** ... 8.1 ± 2.0 µm and 0.9 ± 0.4 µm"
判定「靶② 的 9:1 是**长:宽**，不是长:厚」，并进一步写下**推论**：

> 「两份同工艺文献给的都是"宽"，**没有一份给"厚"** ⇒ 板条厚这个量同工艺文献里不存在」

⛔⛔ **这条推论是错的，本轮已核实。** 重新逐字核对 `docs/refcheck/REFERENCE_AUDIT.md`：

* `:56`（**方法节**）：
  > "martensite lath **thickness** was measured from BSE images using the
  >  **linear intercept method** specified in the GB/T 6394-2017 … at least n ≥ 300 intercepts"
* `:62`：`"At P = 173 W, the measured lath **thicknesses** span approximately **0.51–0.88 µm**."`
* `:64`：`"At P = 193 W, α' martensite lath **thickness** became more uniform …"`
  （摘要、方法、结果**全用 thickness**；只有结果叙述里那**一句**用了 "width"）

⇒ **Shuai 2026 给的就是"板条厚" 0.51–0.88 µm（线性截距法，n≥300），是同工艺同材料的厚度锚点。**

**⇒ 正确的状态（三方证据）**

| 来源 | 量 | 值 | 方法 | 用词 |
|---|---|---|---|---|
| Wang 2026 | 长 | **8.1 ± 2.0 µm** | EBSD IPF（2D 截面） | length |
| Wang 2026 | "宽" | **0.9 ± 0.4 µm** | 同上 | **width** |
| Shuai 2026 | **厚** | **0.51–0.88 µm** | BSE + **线性截距法** | **thickness** |

**关键观察**：Wang 的 "width" 0.9 ± 0.4 µm 与 Shuai 的 "thickness" 0.51–0.88 µm
**在数值上重合** ⇒ **两份同工艺文献很可能在量同一个"短横向尺寸"、只是用词不同**。
⇒ **此前的原始读法「长:厚 ≈ 9:1」很可能是对的**；而"长:宽"是另一种同样合理的读法。
**仅凭这两句话无法判定。** ⇒ **正确的做法是：两个轴都报，靶写成区间并标注口径存疑。**

**⇒ 由两篇组合出的可引用区间（**跨文献**，须标注）**
    长 ÷ 厚 = 8.1 / 0.88 … 8.1 / 0.51 = **9.2 – 15.9**  ⇒ **≈ 9–16**
    （Wang 只给长、"宽"；Shuai 只给"厚"——合起来才是 长:厚）

本脚本只改**"同工艺文献没有厚"这一族错误推论**，逐条打印 before/after；
**找不到就 FAIL**（不静默跳过）。用法：`python3 _fix_overcorrect.py [--apply]`
"""
import os
import re
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))

# 逐文件、逐锚点的精确替换（每条必须命中恰好 1 次）
PLAN = {
    'T24_verify_grouping.py': [
        ("""      ⚠ 另外两份同工艺文献给的都是"宽"、**没有一份给"厚"**：""",
         """      ✅ **但"厚"是有同工艺锚点的**（本文件 Round 139 第三轮纠正了上一轮的过度纠正）："""),
        ("""      ⇒ **"板条厚"这个量同工艺文献里不存在** ⇒ `L/T` 只能作"模型自身值"报，**无靶**。""",
         """      ⇒ Shuai 2026 给的就是**板条厚** 0.51–0.88 µm（BSE + **线性截距法** n≥300，
         `REFERENCE_AUDIT.md:56/62` 逐字）⇒ 由两篇组合得 **长:厚 ≈ 8.1/0.88 … 8.1/0.51 = 9.2–15.9**。
      ⇒ **`L/T` 有靶，但它是"跨两篇同工艺文献"的组合值 ⇒ 必须标注。**"""),
        ("""    #     ⇒ **`geom_ar()` 目前没有任何同工艺同材料靶**（两份同工艺文献给的都是"宽"：
    #     Wang 2026 length 8.1 / **width** 0.9；Shuai 2026 "lath **widths** 0.51–0.68 µm"）。""",
         """    #     ⇒ 但 **`geom_ar()` 是**有靶的**：Shuai 2026 给的正是**板条厚** 0.51–0.88 µm
    #     （BSE + 线性截距法，`REFERENCE_AUDIT.md:56/62` 逐字）⇒ 与 Wang 的长 8.1 µm 组合
    #     得 **长:厚 ≈ 9.2–15.9**。⚠ 跨文献组合，须标注。"""),
        ("""        print('     ⛔ **本行没有同工艺同材料靶**：两份同工艺文献给的都是**宽** —— '""",
         """        print('     ✅ **本行的靶**（⚠ **跨两篇同工艺文献组合**，须标注）：长 ÷ 厚 = '"""),
        ("""              ' ⇒ **"板条厚"这个量同工艺文献里不存在**，只能作"模型自身值"报。')""",
         """              ' ⇒ **长:厚 ≈ 9.2–15.9**（Wang 只给长、"宽"；Shuai 只给"厚"）。')"""),
        ("""              '两份同工艺文献给的都是**宽** —— Wang 2026 length 8.1 / **width** 0.9 µm；'""",
         """              'Shuai 2026 **lath thickness** 0.51–0.88 µm（BSE + 线性截距法）；'"""),
    ],
    'WINDOWB_DELIVERY.md': [
        ("""> （`docs/refcheck/ref01_shuai2026.txt:299` 逐字）⇒ **"板条厚"这个量在同工艺文献里没有。**""",
         """> ⚠ **但 Shuai 2026 的方法节用的是 "lath thickness"（线性截距法）** ⇒ **板条厚是有同工艺锚点的**
> （0.51–0.88 µm）⇒ 由两篇组合得 **长:厚 ≈ 9.2–15.9**。上面那句"没有厚"**已作废**。"""),
    ],
    'WINDOWB_ROADMAP_TO_CORRECT.md': [
        ("""3. **板条"厚"这个量在同工艺文献里不存在** ⇒ 模型报的厚度只能标为"模型自身值，无同工艺靶"；""",
         """3. **板条"厚"有同工艺锚点**（Shuai 2026 的**方法节**就是 "lath **thickness**" + 线性截距法，
   0.51–0.88 µm）⇒ 与 Wang 的长 8.1 µm 组合得 **长:厚 ≈ 9.2–15.9**（跨文献，须标注）；"""),
    ],
    '_fix_9to1.py': [
        ("""⇒ **两份同工艺同材料文献给的都是"宽"，没有一份给"厚"。**""",
         """⛔ **更正（同日第三轮）**：上面这句推论**是错的** —— Shuai 2026 的**方法节**用的是
"lath **thickness**"（线性截距法，0.51–0.88 µm）⇒ **"厚"是有同工艺锚点的**。
见 `_fix_overcorrect.py`。Wang 的 "width" 与 Shuai 的 "thickness" **数值重合**
⇒ 两份很可能在量**同一个短横向尺寸** ⇒ 既有读法**不能判定谁对**。"""),
    ],
}

ok = True
tot = 0
for fn, subs in PLAN.items():
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        print('FAIL: 缺文件 %s' % fn); ok = False; continue
    s = open(p, encoding='utf-8').read()
    n = 0
    for old, new in subs:
        c = s.count(old)
        if c != 1:
            print('FAIL: %s 锚点出现 %d 次（应为 1）：%r' % (fn, c, old[:70])); ok = False
            continue
        s = s.replace(old, new); n += 1
        print('OK   %-30s %s' % (fn, old.strip().split('\n')[0][:66]))
    tot += n
    if a.apply:
        open(p, 'w', encoding='utf-8', newline='\n').write(s)

print('\n' + '=' * 90)
print('命中 %d 条；模式：%s' % (tot, '**已写回**' if a.apply else '**仅预览**'))
if not ok:
    print('⛔ 有锚点未命中 ⇒ 若已写回则处于**半途状态**，需人工核'); sys.exit(1)
print('=' * 90)
