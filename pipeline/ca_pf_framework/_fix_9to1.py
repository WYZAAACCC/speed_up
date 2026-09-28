#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_fix_9to1.py --- 一次性口径纠正：**Wang 2026 的 9:1 是「长:宽」，不是「长:厚」**

错误来源（Round 139 复核）
--------------------------
`docs/refcheck/REFERENCE_AUDIT.md:86` 的**逐字原文**是：

    "The average **length and width** of these platelets are 8.1 ± 2.0 µm
     and 0.9 ± 0.4 µm, respectively."

同文件 `:95` 也**正确地**记作「长 8.1±2.0 µm × **宽** 0.9±0.4 µm」。
**但下游**（探针打印、T21/T24 打印、多份 md）一路写成
「几何**长:厚** ≈ 9:1」⇒ **把"宽"当成了"厚"**，且 `WINDOWB_AUDIT_REGISTER.md:82`
自己写着「长 × **宽** 8.1 × 0.9 ⇒ 几何**长:厚** ≈ 9:1」——**同句自相矛盾**。

顺带核实 Shuai 2026（`docs/refcheck/ref01_shuai2026.txt:299`）也是**宽度**：
    "with lath **widths** between 0.51 and 0.68 µm"
⇒ **两份同工艺同材料文献给的都是"宽"，没有一份给"厚"。**

⇒ 正确口径
----------
* **靶② = 几何长 : 宽 ≈ 9 : 1**（Wang 2026，LPBF Ti-64 as-built α′，EBSD IPF，2D 截面）
  ⇒ 它能锚定 **`β_w = ln 9 ≈ 2.20`**（当前值 2.3 数量级相近，但**出处曾是错的**）；
* **板条"厚"：同工艺同材料无锚点** ⇒ 只能报"模型自身值，无同工艺靶"；
  `β_h` 的唯一有归属输入仍是 §9.3 路径 (i) 的 **3.8**（Ti-64 位错环能量）。

本脚本只动**把 9:1 归给 Wang/8.1×0.9 的那些位置**，逐条打印 before/after 供复核；
**找不到就报 FAIL**（不静默跳过）。用法：`python3 _fix_9to1.py [--apply]`
"""
import os
import re
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true', help='真正写回；不给则只预览')
a = ap.parse_args()

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # 仓库根
TARGETS = [
    os.path.join(HERE, 'MEASUREMENT_SPEC.md'),
    os.path.join(HERE, 'LATH_FACET_PLAN.md'),
    os.path.join(HERE, 'WINDOWB_AUDIT_REGISTER.md'),
    os.path.join(HERE, 'WINDOWB_DELIVERY.md'),
    os.path.join(HERE, 'T_RESULTS_T1_T5.md'),
    os.path.join(HERE, 'T21_beta_calib.py'),
    os.path.join(HERE, 'T24_verify_grouping.py'),
    os.path.join(HERE, '_probe_LT.py'),
    os.path.join(ROOT, 'pipeline', 'ca_pf_framework', 'WINDOWB_ROADMAP_TO_CORRECT.md'),
]

# --- 只匹配"把 9:1 归给 Wang / 8.1×0.9"的行 -------------------------------------
LINE_HIT = re.compile(r'(9\s*:\s*1|≈\s*9\b)')
ATTR = re.compile(r'(Wang|8\.1|0\.9\s*±)')

# 行内替换：长:厚 → 长:宽（仅在这些行上）
SUBS = [
    (re.compile(r'几何长:厚'), '几何长:宽'),
    (re.compile(r'长:厚'), '长:宽'),
    (re.compile(r'长厚比'), '长宽比'),
    (re.compile(r'长÷厚'), '长÷宽'),
]

changed = []
missed = []
for path in TARGETS:
    if not os.path.exists(path):
        missed.append((path, '文件不存在'))
        continue
    src = open(path, encoding='utf-8').read()
    lines = src.split('\n')
    n = 0
    for i, ln in enumerate(lines):
        if LINE_HIT.search(ln) and ATTR.search(ln) and ('长:厚' in ln or '长÷厚' in ln
                                                        or '长厚比' in ln):
            new = ln
            for pat, rep in SUBS:
                new = pat.sub(rep, new)
            new = new.replace('几何长:宽 ≈ 9:1', '几何长:宽 ≈ 9:1（Wang 2026 原文 = length 8.1 µm / **width** 0.9 µm）')
            if new != ln:
                lines[i] = new
                n += 1
                print('  [%s:%d]\n    - %s\n    + %s' % (os.path.basename(path), i + 1,
                                                         ln.strip()[:150], new.strip()[:150]))
    if n:
        changed.append((path, n))
        if a.apply:
            open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
    else:
        missed.append((path, '本文件没有命中行'))

print('\n' + '=' * 92)
print('命中并修正：%d 个文件 / %d 行' % (len(changed), sum(n for _, n in changed)))
for p, n in changed:
    print('   %-46s %d 行' % (os.path.basename(p), n))
if missed:
    print('⚠ 未命中（需人工确认是否确实无需改）：')
    for p, why in missed:
        print('   %-46s %s' % (os.path.basename(p), why))
print('模式：%s' % ('**已写回**' if a.apply else '**仅预览**（加 --apply 写回）'))
print('=' * 92)
print('⛔ 注意：本脚本**只改"把 9:1 归给 Wang"的措辞**，不改任何数值、不改模型的 L/T 口径。')
print('   仍须人工补的三处（脚本不碰）：')
print('   1) 凡"板条厚 0.51–0.68 µm（Shuai 2026）"⇒ 原文是 **lath widths**，须标为"宽"或注明口径存疑；')
print('   2) 凡把 `ΔL/ΔT` 与 9:1 比较的地方 ⇒ 靶② 是 **长:宽**，应比 `ΔL/ΔW`；')
print('   3) `WINDOWB_AUDIT_REGISTER.md` 里"长÷厚几何比是有的"那条注记 ⇒ 整条作废重写。')
