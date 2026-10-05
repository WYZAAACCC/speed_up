#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pdfctl.py —— 正对照：确认 PyMuPDF 能在「中文路径 + F: 盘（9p）」下真正读到内容。
判据：必须打印出非空的 title/text；若 0 字节则工具不可用，后面的索引工作全部无效。
"""
import os
import time

import pymupdf

SRC = "/mnt/f/参考论文/马氏体仿真"


def main() -> int:
    fs = sorted(os.listdir(SRC))
    print(f"目录可见 {len(fs)} 项")
    t0 = time.time()
    ok = 0
    for f in fs[:5]:
        p = os.path.join(SRC, f)
        with pymupdf.open(p) as d:
            n_pages = d.page_count          # ← 必须在 with 内取，出了块文档就关了
            txt = d[0].get_text()
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        print(f"\n--- {f[:70]}")
        print(f"    pages={n_pages} chars={len(txt)}")
        for ln in lines[:4]:
            print(f"    | {ln[:140]}")
        if len(txt) > 200:
            ok += 1
    print(f"\n正对照：{ok}/5 篇首页文本 >200 字符；用时 {time.time()-t0:.2f}s")
    return 0 if ok >= 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
