#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_run_one.py <tag> [<beta_h>] —— 单臂启动器（与 `_t11_cube2b.py` 同参数，便于并行插入）。

参数与 `_t11_cube2b.py` **逐字一致**（同一 COMMON），便于与主控跑的臂直接合并判定。
默认核 = 250 nm 立方（`R1/R3 = 1`）。
"""
import subprocess
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"
N, CUBE, STEPS = 128, 250.0, 1000
DIM = {  # 臂 → (plate_L, plate_W, plate_T)
    "c2PosA": (1250.0, 1250.0, 1250.0 / 9.0),   # 正对照：核 R1/R3 ≈ 9
    "c2Arch3": (CUBE, CUBE, CUBE / 3.0),        # 归档式扁核：核 R1/R3 ≈ 3
}

tag = sys.argv[1]
bh = sys.argv[2] if len(sys.argv) > 2 else "6.477"
pl, pw, pt = DIM.get(tag, (CUBE, CUBE, CUBE))
argv = [
    PY, "-u", "_bk_exp.py",
    "--N", str(N), "--dx-nm", "62.5", "--steps", str(STEPS),
    "--every", "100", "--snap-every", "100", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "8", "--arm", "dry",
    "--plate-L", str(pl), "--plate-W", str(pw), "--plate-T", str(pt),
    "--nuc-shape", "disc", "--grow-stack",
    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-h", bh, "--beta-w", "0.0", "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "0.0",
    "--facet-proj", "0", "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--out", OUT, "--tag", tag,
]
log = "/mnt/f/speed_up/_w2_%s.log" % tag
print("tag=%s beta_h=%s plate=%.0f x %.0f x %.1f nm (核 R1/R3 = %.2f)"
      % (tag, bh, pl, pw, pt, pl / pt))
with open(log, "w") as fh:
    rc = subprocess.call(argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print("退出码 = %d  日志=%s" % (rc, log))
