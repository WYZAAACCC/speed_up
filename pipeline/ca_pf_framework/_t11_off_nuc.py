#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_off_nuc.py —— 验证 `--laths 1` 是否把 `nuc_init` 强制归零（⇒ 形核通道全关）。

判据（`_bk_exp.py` 的 `nuc_mode` 自动逻辑）：若 `len(laths)==1` ⇒ `nuc_init` 归 0。
"""
import argparse
import io
import sys

sys.argv = ["x"]
# 复刻 `_bk_exp.py` 的自动逻辑（只读它自己的代码，不 import 引擎）
import re

src = open("/mnt/f/speed_up/pipeline/ca_pf_framework/_bk_exp.py",
           encoding="utf-8").read()
idx = src.find("nuc_mode")
# 找 nuc_init 被强制置零的行
for m in re.finditer(r'.{0,200}nuc_init\s*=\s*0.{0,200}', src, re.S):
    t = m.group(0)
    if 'laths' in t or 'len(' in t:
        print("── 候选片段 ──")
        print(t.strip()[:400])
        print()
