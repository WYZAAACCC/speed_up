#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_D5_code.py —— **D5 ②：逐项对代码查"厚度定标机制"的缺失**。

## 背景（`R665` 已证）
文献**无法分离** width 与 thickness（只有 2D 长:短）⇒ "厚度靶"口径须改。
但**模型内部**仍可问：**本模型里"厚度"这一维是被什么定住的？**
`LATH_FACET_PLAN` 主因③ 声称"**板片厚只由核数密度 + 生长时间定**" ⇒ 本工具逐项核实。

## 做法
在引擎里搜与"厚度/背应力/自协调/钉扎"相关的机制，逐个查它**是否存在**、**是否被启用**。
⚠ 只读代码 + 读 CSV，不跑仿真。
"""
import os
import re

SRC = "/mnt/f/speed_up/pipeline/ca_pf_framework/windowB_surface.py"
txt = open(SRC, encoding="utf-8", errors="replace").read()
lines = txt.splitlines()
print("=" * 100)
print("D5 ②：逐项核实『厚度定标机制』在引擎里是否存在 / 是否启用")
print("  源：%s（%d 行）" % (os.path.basename(SRC), len(lines)))
print("=" * 100)
# 机制清单（每条：名称 / 搜索正则 / 期望）
MECH = [
    ("背应力（back stress）",
     r"back_?stress|背应力", "板条间弹性自协调产生背应力 ⇒ 厚度自限"),
    ("弹性自协调（self-accommodation）",
     r"selfac|self_accommod|自协调", "自协调变体组降低弹性能 ⇒ 定厚度"),
    ("孪晶/层错尺度",
     r"twin|stacking|孪晶|层错", "真实板条厚的下限由孪晶/层错尺度定"),
    ("界面能-弹性能竞合（临界厚度）",
     r"critical_thick|crit_thick|临界厚度", "γ/Δf 与弹性能竞争 ⇒ 临界厚度"),
    ("板条间钉扎（pinning/arrest）",
     r"pin|arrest|停止|钉扎", "厚度停止机制"),
    ("薄片 Gibbs-Thomson 阻力",
     r"gibbs|thomson|曲率惩罚", "薄片高曲率 ⇒ 额外阻力"),
    ("逐变体各向异性弹性",
     r"per_var_el|variant_aniso|逐变体", "各变体弹性各向异性 ⇒ 厚度定标"),
]
for name, pat, why in MECH:
    hits = [(i + 1, l.strip()) for i, l in enumerate(lines) if re.search(pat, l, re.I)]
    print("\n  【%s】" % name)
    print("     物理含义：%s" % why)
    print("     代码命中：**%d** 处" % len(hits))
    for ln, l in hits[:4]:
        print("       :%d  %s" % (ln, l[:96]))
print()
print("=" * 100)
print("D5 ② 结论的判读规则（先登记）")
print("  · 命中 0 处 ⇒ **该机制在引擎里不存在**")
print("  · 命中但只在注释/deprecated ⇒ 需人工判（本工具会打印原文供判）")
print("  · `LATH_FACET_PLAN` 主因③ 的声称（'厚度只由核数密度+生长时间定'）")
print("    若成立 ⇒ 上表中的机制应当**全部缺失或无路径**")
