#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_murz_scan.py —— 从 Murzinova 2017 原文抽：**方法**（测的是哪种界面）与**数值**。

判据（可 FAIL，③ 的七道纪律之"跨机制"与"量纲/定义"）：
  * 若原文明确是 **α/β（扩散型）**（层片 α + β，加热保温形成）
    ⇒ 本项目把它当作 **α′/β（位移型）** 用 ⇒ **必须标「跨机制借用」并降权**；
  * 数值必须与代码里的 `GAMMA_AB = dict(T600C=(0.298,0.429), T975C=(0.201,0.337))`
    **逐项对上**（否则是"记错了"）。
"""
import re

import pymupdf

doc = pymupdf.open("/tmp/murz.pdf")
full = "\n".join(doc[p].get_text() for p in range(doc.page_count))
print(f"=== 共 {doc.page_count} 页，{len(full)} 字符 ===")

print("\n########## ① 摘要（判『测的是哪种界面』）##########")
head = full[:2200]
for ln in head.splitlines():
    s = ln.strip()
    if s:
        print("  " + s[:150])

print("\n########## ② 含数值的行（γ / J/m² / mJ/m²）##########")
NU = re.compile(r"(J\s*/\s*m|mJ\s*/\s*m|\b0\.\d{3}\b|\b0\.\d{2}\b)", re.I)
KEY = re.compile(r"(energy|γ|gamma|interface|specific)", re.I)
seen = set()
for ln in full.splitlines():
    s = ln.strip()
    if s and KEY.search(s) and NU.search(s) and s not in seen:
        seen.add(s)
        print("  " + s[:160])

print("\n########## ③ 出现 '600' / '975' / 'α′' / 'alpha prime' 的行 ##########")
T = re.compile(r"(600|975|α\s*[′']|alpha\s*prime|martensit|displaciv|diffus)", re.I)
for ln in full.splitlines():
    s = ln.strip()
    if s and T.search(s):
        print("  " + s[:160])
