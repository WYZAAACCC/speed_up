#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_facet_arm.py <tag> <wulff 0|1> —— (1) 刻面生长 A/B 单臂。

## 目的
测**长/宽速度比** `v_a/v_w`：基线（`mob_wulff=0`）应落 **1.6–2.0**，
开启 Wulff 凸化（`mob_wulff=1`）应升到 **≥7**（解析 9.9 的 70%）。
依据：`_bk_exp.py:4675-4680`（E-1：三种平流格式都只给 1.6–2.0，凸化预言 9.9）。

## 配置（单变量：只有 `--mob-wulff` 不同）
  · **小盒 `N=64`（4 µm）**：只为测速度比，不需要大盒 ⇒ 省算力（每步 ~0.3 s）
  · 核 = **250 nm 立方**（等轴）⇒ 伸长完全来自生长
  · `--grow-stack --nuc-init 0` ⇒ 只播 1 片
  · `--steps 300`、`--snap-every 25` ⇒ 12 个点，够量速度比
  · `--band-cells` 可传（默认 20）
"""
import subprocess
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"

tag = sys.argv[1]
wulff = int(sys.argv[2]) if len(sys.argv) > 2 else 0
band = sys.argv[3] if len(sys.argv) > 3 else "20"
bh = sys.argv[4] if len(sys.argv) > 4 else "6.477"      # ★ 物理值 A/B（默认=生产值）

argv = [
    PY, "-u", "_bk_exp.py",
    "--N", "64", "--dx-nm", "62.5", "--steps", "300",
    "--every", "25", "--snap-every", "25", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--plate-L", "250.0", "--plate-W", "250.0", "--plate-T", "250.0",
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
    "--band-cells", band,
    "--out", OUT, "--tag", tag,
]
if wulff:
    argv.append("--mob-wulff")
log = "/mnt/f/speed_up/_w2_%s.log" % tag
print("tag=%s  mob_wulff=%d  band_cells=%s" % (tag, wulff, band), flush=True)
with open(log, "w") as fh:
    rc = subprocess.call(argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print("退出码 = %d  日志=%s" % (rc, log))
