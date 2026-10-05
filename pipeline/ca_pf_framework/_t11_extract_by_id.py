#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_extract_by_id.py —— 按目录内**序号**抽 PDF 全文（绕开所有引号/编码问题）。

用法: _t11_extract_by_id.py <序号> [关键词...]
不带参数时先列出目录（带序号）。
"""
import os
import re
import sys

import pymupdf

PDFDIR = "/mnt/f/参考论文/马氏体仿真"
OUTDIR = "/mnt/f/speed_up/_litidx/lit_txt"
files = sorted(f for f in os.listdir(PDFDIR) if f.lower().endswith(".pdf"))


def main() -> int:
    if len(sys.argv) < 2:
        for i, f in enumerate(files):
            print(f"{i:4d}  {f}")
        return 0
    idx = int(sys.argv[1])
    kws = sys.argv[2:] or ["block", "lath", "thickness", "packet", "variant",
                           "aspect", "width", "self-accommodat", "nucleat",
                           "µ m", "µm", "mobility", "interfacial"]
    fn = files[idx]
    p = os.path.join(PDFDIR, fn)
    print(f"[{idx}] {fn}")
    with pymupdf.open(p) as d:
        npages = d.page_count
        txt = "\n".join(f"\n===== PAGE {i+1}/{npages} =====\n" + d[i].get_text()
                        for i in range(npages))
    os.makedirs(OUTDIR, exist_ok=True)
    stem = re.sub(r"[^0-9A-Za-z._\u4e00-\u9fff-]+", "_", os.path.splitext(fn)[0])[:110]
    out = os.path.join(OUTDIR, stem + ".txt")
    with open(out, "w", encoding="utf-8", errors="replace") as fh:
        fh.write(f"# SRC: {p}\n{txt}")
    print(f"页数 {npages}  字符 {len(txt)}  ⇒ {out}\n")
    print("=" * 90 + "\n=== 首页 ===\n" + "=" * 90)
    print(txt[:2600])
    flat = re.sub(r"[ \t]+", " ", txt)
    for kw in kws:
        hits = [m.start() for m in re.finditer(re.escape(kw), flat, re.I)]
        if not hits:
            continue
        print(f"\n{'='*90}\n### {kw!r}: {len(hits)} 处（前 6 处上下文）\n{'='*90}")
        for h in hits[:6]:
            s, e = max(0, h - 300), min(len(flat), h + 300)
            print("  …" + flat[s:e].replace("\n", " ") + "…\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
