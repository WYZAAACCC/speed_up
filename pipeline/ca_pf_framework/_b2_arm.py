#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_arm.py <tag> <order> —— **B2 专用启动器**。

## 为什么新写一个（而不是改 `_t11_facet_arm.py`）
* `_t11_facet_arm.py` 没有 `--facet-proj-order` 参数（它只传 `--facet-proj`）；
* ⛔ 我第一版长程 A/B 直接调 `_bk_exp.py`、**漏了 `--plate-*/--nuc-*/--grow-stack`**
  ⇒ 播种行为与 `C4` **完全不同**（`step 0`：`nslab=6` vs `1`）⇒ **那一轮作废**（`R695` 记账）。
⇒ 本脚本的 argv **逐条照抄 `_t11_facet_arm.py:86-105`**（保证与 `C4`/`G4` 同口径），
  **只在末尾加 `--facet-proj-order`**（`B2-D7` 单变量）。

## 用法
  `_b2_arm.py B2P_dip4_pre pre`
  `_b2_arm.py B2P_dip4_post post`
"""
import os
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"

tag = sys.argv[1]
order = sys.argv[2]

# ---- 逐条照抄 `_t11_facet_arm.py:86-105`（`C4` 的口径）----
argv = [
    "--N", "96", "--dx-nm", "62.5", "--steps", "400",
    "--every", "25", "--snap-every", "25", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--plate-L", "125.0", "--plate-W", "125.0", "--plate-T", "125.0",
    "--nuc-shape", "disc", "--grow-stack",
    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--nuc-mode", "auto", "--eng-cadence", "30",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-h", "6.477", "--beta-w", "2.3", "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "4.0",
    "--facet-proj", "1", "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--band-cells", "40",
    "--mob-wulff",                      # = `C4`（wulff=1）
    # ★ B2 唯一新增（单变量）
    "--facet-proj-order", order,
    "--out", "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
    "--tag", tag,
]
cmd = [PY, "-u", "_bk_exp.py"] + argv
print(" ".join(cmd))
sys.exit(subprocess.run(cmd, cwd=FW).returncode)
