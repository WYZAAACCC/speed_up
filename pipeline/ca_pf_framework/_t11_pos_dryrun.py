#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pos_dryrun.py —— **压边界**：正对照臂用 `plate_T = 250/9 = 27.8 nm`
（`Δx = 62.5 nm` ⇒ 仅 **0.44 格**）⇒ 引擎会不会拒播？

只跑 **2 步**（够走到播种+一次输出），看退出码与 banner 的播种报告。
判据：若退出码 ≠ 0 或 banner 报"拒播/出盒/margin 负" ⇒ 正对照臂须改用别的做法。
"""
import os
import subprocess

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"
CUBE = 250.0
argv = [
    PY, "-u", "_bk_exp.py",
    "--N", "128", "--dx-nm", "62.5", "--steps", "2",
    "--every", "1", "--snap-every", "1", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--plate-L", str(CUBE), "--plate-W", str(CUBE),
    "--plate-T", str(CUBE / 9.0),          # ★ 0.44 格
    "--nuc-shape", "disc", "--grow-stack",    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-h", "6.477", "--beta-w", "0.0", "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "0.0",
    "--facet-proj", "0", "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--out", OUT, "--tag", "c2PosDry",
]
log = "/mnt/f/speed_up/_w2_c2PosDry.log"
with open(log, "w") as fh:
    rc = subprocess.call(argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print("退出码 = %d" % rc)
txt = open(log, encoding="utf-8", errors="replace").read()
import re
for pat in (r'.*实际播种.*', r'.*播种 \d+ 片.*', r'.*margin.*', r'.*拒.*',
            r'.*ValueError.*', r'.*Traceback.*', r'^\s*\[\s*\d+\].*'):
    for m in re.findall(pat, txt, re.M)[:3]:
        print("  " + m.strip()[:170])
print("\n⇒ %s" % ("✅ 30 nm 厚的核可播（正对照臂可行）" if rc == 0
                 else "❌ **退出码非 0 ⇒ 正对照臂须改做法**"))
