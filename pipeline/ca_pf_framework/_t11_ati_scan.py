#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_ati_scan.py —— ②③-9：从 ATI Ti-6Al-4V 数据表里抽**高温力学数据**。

判据（可 FAIL）：
  * 若表里有 **600 °C / 873 K 附近的屈服强度** ⇒ 采纳为 `sigma_y(873 K)` 的**候选值**；
  * 若只有室温值 ⇒ **该来源不能回答 873 K**，如实记录（不得用室温值代替）。
"""
import re

import pymupdf

doc = pymupdf.open("/tmp/ati64.pdf")
print(f"=== {doc.page_count} 页 ===")
KEY = re.compile(r"yield|proof|0\.2|elevated|temperatur|°\s*C|K\b|MPa|ksi", re.I)
for pno in range(doc.page_count):
    txt = doc[pno].get_text()
    lines = txt.splitlines()
    print(f"\n########## p{pno+1}（{len(lines)} 行）##########")
    for ln in lines:
        s = ln.strip()
        if s and KEY.search(s):
            print("  " + s[:170])
