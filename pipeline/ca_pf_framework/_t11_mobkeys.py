#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_mobkeys.py <tag>... —— 列出 `meta.json` 里**全部 `mob*` 键**。

## 为什么必须查（`R690`）
`R663` 已证：**`mob_dip` 只在 `mob_wulff=1` 时被消费**（入口条件 `windowB_surface.py:5159`）。
⇒ 但 `meta.json` **是否落了 `mob_wulff`** 决定了"事后能否自证 `dip` 生效"。
**⇒ 本工具把每个臂的全部 `mob*` 键打出来。**
"""
import json
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for t in (sys.argv[1:] or ["F8", "C4", "F6", "G4", "W0", "W4"]):
    p = os.path.join(ROOT, "dry_%s" % t, "meta.json")
    if not os.path.exists(p):
        print("  %-6s 无 meta.json" % t)
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("  %-6s 读失败 %s" % (t, e))
        continue
    mob = {k: v for k, v in d.items() if k.lower().startswith("mob")}
    fac = {k: v for k, v in d.items() if "facet" in k.lower()}
    band = {k: v for k, v in d.items() if "band" in k.lower()}
    nuc = {k: v for k, v in d.items() if "nuc" in k.lower() or "eng" in k.lower()}
    print("  %-6s mob=%s" % (t, mob if mob else '**无**'))
    print("         facet=%s  band=%s" % (fac if fac else '**无**', band if band else '**无**'))
    print("         nuc/eng=%s" % (nuc if nuc else '**无**'))
