#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_fix_shuai_interchange.py --- **第二次纠错**：Shuai 用的是**同一个测量**的两个词

来源（子代理全检索，`lit_tmp/ALPHA_PRIME_LATH_WIDTH_PROVENANCE.md`，两份**全文**均已取到）
----------------------------------------------------------------------------------------
* **Shuai 2026**（`10.3390/ma19061049`, PMC13027919）逐字：
  * §2.2：「EBSD was used primarily for crystallographic orientation and texture analyses,
    whereas the α/α' lath morphology and **lath width** were measured and quantified from
    the BSE micrographs.」
  * §2.2：「The α' martensite **lath thickness** was measured from BSE images using the
    **linear intercept method** specified in the GB/T 6394-2017.」
  * §3.2：「… with **lath widths** between 0.51 and 0.68 μm.」
  * Fig.6 文字：「the measured **lath thicknesses** span approximately 0.51–0.88 μm.」
  ⇒ **同一篇里 "width" 与 "thickness" 指**同一个 2D BSE 线性截距测量**（一条平均弦长），
    **不是两个不同的尺寸。** 该文**没有报 lath 长度**。
* **Wang 2026**（`10.20517/microstructures.2025.144`）逐字：
  「The average **length and width** of these platelets are 8.1 ± 2.0 µm and 0.9 ± 0.4 µm.」
  方法 = **EBSD IPF，plane-view（⊥ 建造方向）** ⇒ **也是 2D 截面**；短向作者叫 **width**。

⇒ **两次都被我读错了**
* `3fab9673`：「9:1 是长:宽、**不是**长:厚」—— 把**一个量**判成了两个；
* `fda6d57f`：「Shuai 给的就是**厚**」—— 同样把**一个量**判成了两个（只是反了一边）。

**⇒ 正确的结论（本脚本要写进代码/文档的）**
1. **文献里的 2D 截面每篇只给"一个长 + 一个短"两个尺寸**，**无法分离宽与厚**。
   ⇒ `β_w` 与 `β_h` 在现有 2D 数据下**退化**（模型比数据多一个参数）。
2. 文献**能约束的只有一个指数**：`ln(长/短) = 2.2–3.2`
   （Wang 2D L:短 = 9.0 ⇒ 2.20；**Xie 2026 未筛样** 2D L:W = 16.7–23.8、均值 20.9 ⇒ 3.04）。
3. **新锚点**：**Xie et al. 2026, *Materials* 19:1945, doi 10.3390/ma19101945**（LPBF Ti-64 as-built，
   BSE 2D，**每试样随机测 50 条板条**、10 个试样）：**长 5.065–5.685 µm，宽 0.239–0.304 µm**
   ⇒ **2D 长:短 = 16.7–23.8（均值 20.9）**，**无预筛**（Ter Haar 的 8.37 有 >20 µm 预筛，不可比）。
4. ⛔ **模型现状不受支持**：`β_h = 3.5` ⇒ 长:短 = **33**，而**任何 2D 实测都不超过 24**；
   且 `β_h − β_w = 1.2` 隐含**截面各向异性 3.32:1**，**无出处**。
5. ✅ **但有一个自洽的读法**：模型自己给出 `ΔW/ΔT ≈ 3.6`（**带状截面**）
   ⇒ 2D 截面将**主要采到"厚"** ⇒ 应与 `L/T` 比 ⇒ 模型实测 **`ΔL/ΔT` = 15.9 ∈ [9, 24]** ✓。

用法：`python3 _fix_shuai_interchange.py [--apply]`
"""
import os
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('--apply', action='store_true')
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))

PLAN = {
    'T24_verify_grouping.py': [
        ("""      ⇒ Shuai 2026 给的就是**板条厚** 0.51–0.88 µm（BSE + **线性截距法** n≥300，
         `REFERENCE_AUDIT.md:56/62` 逐字）⇒ 由两篇组合得 **长:厚 ≈ 8.1/0.88 … 8.1/0.51 = 9.2–15.9**。
      ⇒ **`L/T` 有靶，但它是"跨两篇同工艺文献"的组合值 ⇒ 必须标注。**""",
         """      ⛔⛔ **2026-09-28 Round 139 第三次纠正（子代理全检索，两份全文均已取到）**：
      Shuai 2026 在**同一篇里把 "lath width" 与 "lath thickness" 用于同一个 2D BSE
      **线性截距**测量**（§2.2 两句、§3.2、Fig.6 逐字，见
      `lit_tmp/ALPHA_PRIME_LATH_WIDTH_PROVENANCE.md`）⇒ **它不是"厚"这个独立量的锚点。**
      **2D 截面每篇只给"一个长 + 一个短"，物理上无法分离宽与厚**
      ⇒ **文献只能约束一个指数**：`ln(长/短) = 2.2–3.2`
      （Wang 2D 长:短 = 9.0 ⇒ 2.20；**Xie 2026 未筛样 2D 长:宽 = 16.7–23.8、均值 20.9** ⇒ 3.04）。
      ⇒ **`β_w` 与 `β_h` 在现有数据下退化；两者都不得声称有独立锚点。**"""),
        ("""              'Shuai 2026 **lath thickness** 0.51–0.88 µm（BSE + 线性截距法）；'""",
         """              '⚠ 但 **2D 截面无法分离宽与厚** ⇒ 文献只约束**一个**指数 '""" ),
    ],
    'MEASUREMENT_SPEC.md': [
        ("""| **板条厚 thickness** | **0.51–0.88 µm** | Shuai 2026，**BSE + 线性截距法（n≥300）**（`REFERENCE_AUDIT.md:56/62` 逐字） |""",
         """| Shuai 的**短横向** | **0.51–0.88 µm** | Shuai 2026，**BSE + 线性截距法（n≥300）**；⚠ **该文对同一个测量同时用 "width" 与 "thickness" 两个词** ⇒ **不是独立的"厚"**（`lit_tmp/ALPHA_PRIME_LATH_WIDTH_PROVENANCE.md`） |
| **Xie 2026 的"宽"** | **0.239–0.304 µm**；**长 5.065–5.685 µm** | **Xie et al. 2026, *Materials* 19:1945, doi 10.3390/ma19101945**，BSE 2D，**每试样随机 50 条板条**、10 试样，**无预筛** ⇒ **2D 长:短 = 16.7–23.8（均值 20.9）** |"""),
    ],
}

ok = True
tot = 0
for fn, subs in PLAN.items():
    p = os.path.join(HERE, fn)
    s = open(p, encoding='utf-8').read()
    for old, new in subs:
        c = s.count(old)
        if c != 1:
            print('FAIL: %s 锚点出现 %d 次（应为 1）：%r' % (fn, c, old[:80])); ok = False; continue
        s = s.replace(old, new); tot += 1
        print('OK   %-28s %s' % (fn, old.strip().split('\n')[0][:60]))
    if a.apply:
        open(p, 'w', encoding='utf-8', newline='\n').write(s)

print('\n' + '=' * 90)
print('命中 %d 条；模式：%s' % (tot, '**已写回**' if a.apply else '**仅预览**'))
if not ok:
    print('⛔ 有锚点未命中'); sys.exit(1)
print('=' * 90)
print('⛔ 本脚本**只**改"Shuai = 独立的厚"这一族说法。仍需人工补（不在此脚本内）：')
print('   1) 靶② 改成「长 : 短横向 ≈ 9–24」并写明**退化**（β_w/β_h 无法由 2D 数据分离）；')
print('   2) `β_h = 3.5`（长:短=33）**超出所有 2D 实测（≤24）** ⇒ 标注"不受支持"；')
print('   3) `β_h − β_w = 1.2` 隐含的**截面各向异性 3.32:1 无出处** ⇒ 标注"假设"。')
