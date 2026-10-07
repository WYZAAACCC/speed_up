#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_smoke.py —— B2 的**冒烟 A/B**：`--facet-proj-order pre|post` 各跑 3 步。

## 判据（`B2-D2` + `B2-D3` 的极小版）
1. **两个 order 都能跑完**（开关被正确接受、不崩）；
2. **落盘的 `meta.json` 里能看到 `facet_proj_order`**（⇒ 配置可自证，`R690` 的教训）；
3. 两者 `Vt` **不完全相同**（⇒ `post` 真的改变了推进顺序，而不是静默无效）。

⚠ 3 步不足以判 `B2-D3` 的形状判据 —— 这一步**只验证管道通**。
"""
import json
import os
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
COMMON = ["--steps", "3", "--N", "64", "--band-cells", "40", "--facet-proj", "1"]

print("=" * 100)
print("B2 冒烟 A/B —— `--facet-proj-order pre|post`，3 步，N=64")
print("=" * 100)
res = {}
for order in ("pre", "post"):
    tag = "B2SM_" + order
    cmd = [PY, "_bk_exp.py"] + COMMON + ["--tag", tag, "--facet-proj-order", order]
    p = subprocess.run(cmd, cwd=FW, capture_output=True, text=True, timeout=900)
    tail = (p.stderr or p.stdout or "").strip().splitlines()
    res[order] = {"rc": p.returncode, "tail": tail[-1] if tail else "(空)"}
    print("  %-5s rc=%-3d  %s" % (order, p.returncode, res[order]["tail"][:86]))

print("\n--- 判据 2：`meta.json` 里能否看到 `facet_proj_order` ---")
for order in ("pre", "post"):
    mp = os.path.join(FW, "_exp/_bk_t5", "dry_B2SM_" + order, "meta.json")
    if not os.path.exists(mp):
        print("  %-5s ⛔ 无 meta.json" % order)
        continue
    d = json.load(open(mp, encoding="utf-8"))
    keys = [k for k in d if "facet" in k.lower() or "proj" in k.lower()]
    print("  %-5s facet/proj 键 = %s" % (order, {k: d[k] for k in keys} or "**无**"))

print("\n--- 判据 3：两臂的 `Vt` 是否不同（`post` 真的生效） ---")
vt = {}
for order in ("pre", "post"):
    cp = os.path.join(FW, "_exp/_bk_t5", "dry_B2SM_" + order, "series.csv")
    if not os.path.exists(cp):
        continue
    import csv
    rows = list(csv.DictReader(open(cp, encoding="utf-8")))
    if rows:
        vt[order] = rows[-1].get("Vt")
print("  pre  Vt = %s" % vt.get("pre"))
print("  post Vt = %s" % vt.get("post"))
if "pre" in vt and "post" in vt:
    print("  ⇒ %s" % ("**不同 ✅（post 生效）**" if vt["pre"] != vt["post"]
                      else "⚠ 相同 ⇒ 可能 post 未生效，需查"))
