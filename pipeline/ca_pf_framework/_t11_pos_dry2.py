#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pos_dry2.py —— 压测**放大的正对照核**（1250×1250×139 nm，核 L/T = 9，厚 2.2 格）。

判据：退出码 = 0 且 step 0 的 **Vt ≈ 0.217 µm³**（= 1.25×1.25×0.139 µm）、
      `nslab ≥ 1`、显著分量 ≥ 1 ⇒ 一个**可分辨的**、核 L/T = 9 的核。
"""
import re
import subprocess

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"
PL = PW = 1250.0
PT = 1250.0 / 9.0            # 138.9 nm = 2.22 格
argv = [
    PY, "-u", "_bk_exp.py",
    "--N", "128", "--dx-nm", "62.5", "--steps", "2",
    "--every", "1", "--snap-every", "1", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--plate-L", str(PL), "--plate-W", str(PW), "--plate-T", str(PT),
    "--nuc-shape", "disc", "--grow-stack",
    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-h", "6.477", "--beta-w", "0.0", "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "0.0",
    "--facet-proj", "0", "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--out", OUT, "--tag", "c2PosDry2",
]
log = "/mnt/f/speed_up/_w2_c2PosDry2.log"
with open(log, "w") as fh:
    rc = subprocess.call(argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print("plate = %.0f x %.0f x %.1f nm  (核 L/T = %.2f, 厚 %.2f 格)"
      % (PL, PW, PT, PL / PT, PT / 62.5))
print("期望 Vt = %.4f µm³ (= %.2f x %.2f x %.3f)"
      % (PL * PW * PT * 1e-9, PL / 1000, PW / 1000, PT / 1000))
print("退出码 = %d" % rc)
txt = open(log, encoding="utf-8", errors="replace").read()
for pat in (r'.*实际播种.*', r'.*margin.*', r'.*拒.*', r'.*ValueError.*',
            r'.*Traceback.*', r'^\s*\[\s*\d+\].*'):
    for m in re.findall(pat, txt, re.M)[:2]:
        print("  " + m.strip()[:170])
