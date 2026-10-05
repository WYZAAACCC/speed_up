#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_extract_pdf.py —— 抽一篇 PDF 的全文到文本，并检索关键词上下文。

用法: _t11_extract_pdf.py "<pdf 路径>" [关键词1 关键词2 ...]
"""
import os
import re
import sys

import pymupdf

PDFDIR = "/mnt/f/参考论文/马氏体仿真"
OUTDIR = "/mnt/f/speed_up/_litidx/lit_txt"


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    p = sys.argv[1]
    if not os.path.isabs(p) or not os.path.exists(p):
        cands = [f for f in os.listdir(PDFDIR)
                 if f.lower().endswith(".pdf") and p.lower() in f.lower()]
        if len(cands) == 1:
            p = os.path.join(PDFDIR, cands[0])
            print(f"[按子串定位] {cands[0]}")
        elif len(cands) > 1:
            print("匹配到多篇，请给更长的子串：")
            for c in cands:
                print("   ", c)
            return 1
        elif not os.path.isabs(p):
            p = os.path.join(PDFDIR, p)
    if not os.path.exists(p):
        print(f"!! 找不到: {p}")
        return 1
    kws = sys.argv[2:] or ["block", "lath", "thickness", "packet", "variant",
                           "aspect", "width", "µm", "self-accommodat", "nucleat"]
    print(f"PDF: {p}")
    with pymupdf.open(p) as d:
        npages = d.page_count
        txt = "\n".join(f"\n===== PAGE {i+1}/{npages} =====\n" + d[i].get_text()
                        for i in range(npages))
    stem = re.sub(r"[^0-9A-Za-z._\u4e00-\u9fff-]+", "_", os.path.splitext(os.path.basename(p))[0])[:110]
    out = os.path.join(OUTDIR, stem + ".txt")
    os.makedirs(OUTDIR, exist_ok=True)
    with open(out, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(f"# SRC: {p}\n{txt}")
    print(f"页数 {npages}，字符 {len(txt)} ⇒ 写到 {out}")

    # 首页（标题/摘要）
    print("\n" + "=" * 90 + "\n=== 首页 ===\n" + "=" * 90)
    print(txt[:2500])

    # 关键词上下文
    flat = re.sub(r"[ \t]+", " ", txt)
    for kw in kws:
        hits = [m.start() for m in re.finditer(re.escape(kw), flat, re.I)]
        if not hits:
            continue
        print(f"\n{'='*90}\n### 关键词 {kw!r}：{len(hits)} 处，前 8 处上下文\n{'='*90}")
        for h in hits[:8]:
            s = max(0, h - 260)
            e = min(len(flat), h + 260)
            seg = flat[s:e].replace("\n", " ")
            print(f"  … {seg} …\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
