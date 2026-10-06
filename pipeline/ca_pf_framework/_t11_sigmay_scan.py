#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_sigmay_scan.py —— ③-9：在**本地全语料**里抽 Ti-64 在 873 K / 600 °C 附近的屈服强度。

## 为什么要专用脚本（而不是我有印象就写）
  `R620:129` 记「Ti-64 位错环形成能 / `sigma_y(873 K)`：**无候选 ⇒ 全库检索**」。
  用户 ③ 要求：**每条留下「查了哪些、为什么认为找不到」的记录**。
  ⇒ 本脚本把「每篇里与温度同现的 MPa 值」全部打出来，**判据可复核**。

## 抽取规则（留痕，便于复核）
  * 在**同一段落/行窗口**内同时出现：`(yield|σy|proof)` 与 `MPa`；
  * 且窗口里出现**温度线索**：`600 °C` / `873 K` / `(600` / `873` / `0.4 Tm` / `0.5 Tm`；
  * 打印命中行 + 前后 1 行，便于人工判"是不是 Ti-64、是不是该温度"。
"""
import os
import re
import sys

DIRS = ["/mnt/f/speed_up/_litidx/lit_txt",
        "/mnt/f/speed_up/lit/cache",
        "/mnt/f/speed_up/lit/A_txt"]
YLD = re.compile(r"yield\s+str|yield\s+stress|proof\s+str|σ\s*[yY]|\bsigma_?y\b",
                 re.I)
MPA = re.compile(r"(\d{2,4}(?:\.\d+)?)\s*MPa")
TCLUE = re.compile(r"(600\s*°?\s*C|873\s*K|0\.[45]\s*T\s*m|0\.[45]\s*T_m|"
                   r"600\s*degrees|temperatures?\s+up\s+to)", re.I)
# 材料线索（只要提到 Ti-64 才留）
MAT = re.compile(r"Ti[-\s]?6Al[-\s]?4V|Ti64|Ti-64|Ti6Al4V", re.I)

maxhits = int(sys.argv[1]) if len(sys.argv) > 1 else 40
n_files = 0
n_hit = 0
for d in DIRS:
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt"):
            continue
        p = os.path.join(d, fn)
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        n_files += 1
        for i, ln in enumerate(lines):
            win = " ".join(lines[max(0, i - 1):i + 2])
            if not (YLD.search(win) and MPA.search(win)):
                continue
            if not TCLUE.search(win):
                continue
            n_hit += 1
            if n_hit <= maxhits:
                tag = "Ti64" if MAT.search(win) else "  ? "
                vals = ", ".join("%s MPa" % m for m in MPA.findall(win)[:4])
                print(f"[{tag}] {fn[:52]:52} L{i+1:<6} {vals}")
                print(f"        {ln.strip()[:150]}")
print(f"\n扫描文件 {n_files} 篇；命中（屈服+MPa+温度线索）{n_hit} 处")
