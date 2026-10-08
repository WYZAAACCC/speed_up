#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_r712_scan3.py —— 扫新提取的 7 篇（只读），找率律/位点密度/自催化/CNT/随机的定量语句。"""
import io
import os
import re
import sys

ROOT = "/mnt/f/speed_up/_litidx/lit_txt_r712"
PATS = [
    ("rate-law", r"nucleation rate|rate of nucleation|dN/dt|dN_?v|nucleation frequency"),
    ("site-density", r"site density|density of nucleation sites|number of nucleation sites|"
                     r"number density of|N_?v\b"),
    ("sitesat/auto", r"site saturat|sites are consumed|exhaust|impingement|autocatalyt"),
    ("athermal", r"athermal|no thermal activation"),
    ("KM", r"Koistinen|Marburger"),
    ("CNT", r"classical nucleation theory|steady.state nucleation|nucleation barrier|"
            r"exp\s*\(\s*.{0,14}G\s*\*"),
    ("stochastic", r"Poisson|stochastic|probabilis"),
]

files = sorted(f for f in os.listdir(ROOT) if f.endswith(".txt"))
print("files:", len(files))
for fn in files:
    p = os.path.join(ROOT, fn)
    L = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    blocks = []
    for tag, pat in PATS:
        rx = re.compile(pat, re.I)
        got = [(i, s.strip()) for i, s in enumerate(L, 1) if rx.search(s)]
        if got:
            blocks.append((tag, got))
    if not blocks:
        continue
    print()
    print("=" * 96)
    print("● " + fn[:92])
    for tag, got in blocks:
        print("   [%s]  %d 行" % (tag, len(got)))
        for i, s in got[:4]:
            print("      :%-5d %s" % (i, s[:140]))
sys.exit(0)
