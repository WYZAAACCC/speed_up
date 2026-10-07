#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_argvchk.py <tag> —— 检查臂的**实际命令行**里 `--mob-dip` 的真实取值。

## 为什么必须做（`R663`）
`E0/E2/E4`（`mob_dip` = 0.0 / 2.0 / 4.0）的 `Λ` 读数**逐位完全相同**。
按仓库 `P7`/`R635` 的教训（`--beta-w 0.0` 曾让七个臂全部作废），
**"参数没传进去"是首要嫌疑** ⇒ 先查命令行，再谈物理解释。

做法：从 `meta.json` 读（引擎把它落盘了），并与启动器 argv 对照。
"""
import json
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
KEYS = ['mob_dip', 'mob_beta', 'mob_beta_w', 'mob_wulff', 'mob_iform',
        'facet_proj', 'band_cells', 'nuc_mode', 'eng_cadence', 'nuc_every',
        'nuc_init', 'grow_stack', 'gamma0']
for tag in (sys.argv[1:] or ["E0", "E2", "E4", "D0", "D2", "D4", "L0", "B40"]):
    p = os.path.join(ROOT, "dry_%s" % tag, "meta.json")
    if not os.path.exists(p):
        print("【%s】无 meta.json" % tag)
        continue
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        print("【%s】读失败: %s" % (tag, e))
        continue
    print("【%s】" % tag)
    for k in KEYS:
        if k in d:
            print("   %-14s = %r" % (k, d[k]))
    print()
