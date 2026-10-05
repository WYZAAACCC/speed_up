#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_prov_ctx.py --- 抽出「出处关键词」附近的**真实原文**，供人工判读。

## 为什么需要它
`_t10_param_audit2.py` 只报"命中"，而本仓 §3 教训明说 **命中 ≠ 可靠**。
且 v1（只扫 .md）与 v2（加扫 .py）对 `DS_REF`/`mob`/`B` 给出**分歧**（"仅标定" vs "文献/DOI"）
⇒ 必须把原文摆出来看，不能用关键词计数下结论。

## 输出
对每个目标参数，列出命中出处关键词的**原文片段**（带文件名与行号前缀），按文件排序。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = sys.argv[1:] or ["DS_REF", "mob", "B"]
KEY = ("文献", "DOI", "doi", "推导", "标定", "实测", "来源", "出处", "引自", "依据")
MAXSEG = 8          # 每个参数最多展示几段

# 排除审计脚本自身（教训：量具不得扫自己）
SELF = ("_t10_param_audit.py", "_t10_param_audit2.py", "_t10_prov_ctx.py")

files = []
for fn in sorted(os.listdir(HERE)):
    if fn in SELF:
        continue
    if fn.endswith(".md") or fn.endswith(".py"):
        p = os.path.join(HERE, fn)
        try:
            if os.path.getsize(p) <= 4_000_000:
                files.append((fn, open(p, encoding="utf-8", errors="replace").read()))
        except Exception:
            pass
print("扫描 %d 个文件（已排除审计脚本自身）\n" % len(files))

for t in TARGETS:
    print("=" * 78)
    print("参数：%s" % t)
    print("=" * 78)
    shown = 0
    for fn, txt in files:
        if shown >= MAXSEG:
            break
        lines = txt.splitlines()
        for ln, line in enumerate(lines, 1):
            if t not in line:
                continue
            # 上下文 ±4 行
            lo = max(0, ln - 5)
            hi = min(len(lines), ln + 4)
            seg = "\n".join(lines[lo:hi])
            kws = [k for k in KEY if k in seg]
            if not kws:
                continue
            print("\n  ── %s : 第 %d 行附近（命中关键词 %s）──" % (fn, ln, kws))
            for j in range(lo, hi):
                mark = ">>" if j == ln - 1 else "  "
                print("   %s %s" % (mark, lines[j][:150]))
            shown += 1
            break
    if shown == 0:
        print("\n  （无含出处关键词的上下文）")
    print()
