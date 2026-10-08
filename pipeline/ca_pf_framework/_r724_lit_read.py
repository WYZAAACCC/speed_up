#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r724_lit_read.py <关键词正则> [文件...] —— 在指定文献里**打印命中上下文**（P29）。

不预设正则对不对：把上下文打出来，由人判"到底有没有界面迁移速度/激活能数据"。
"""
import os
import re
import sys

D = '/mnt/f/speed_up/_litidx/lit_txt_all'
KEY = sys.argv[1]
FILES = sys.argv[2:] or None
pat = re.compile(KEY, re.I)
if FILES is None:
    FILES = [f for f in sorted(os.listdir(D)) if f.endswith('.txt')
             and re.search(r'martensit|kinetic|titanium|ti.?6al', f, re.I)]
for f in FILES:
    p = f if os.path.isabs(f) else os.path.join(D, f)
    if not os.path.exists(p):
        continue
    txt = open(p, encoding='utf-8', errors='ignore').read()
    ms = list(pat.finditer(txt))
    if not ms:
        continue
    print('=' * 100)
    print('%s   （%d 处命中）' % (os.path.basename(p)[:86], len(ms)))
    print('=' * 100)
    for m in ms[:8]:
        s = max(0, m.start() - 160)
        e = min(len(txt), m.end() + 220)
        print('  …%s…' % txt[s:e].replace('\n', ' '))
        print()
