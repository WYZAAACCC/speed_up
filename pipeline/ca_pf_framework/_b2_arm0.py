#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_arm0.py <tag> —— **`B2-D3②` 的真对照**：与 `B2P_*` 逐条同参，**只有 `--facet-proj 0`**。

## 为什么必须新跑（`R695`/`R696` 的账）
`R674` 的 **"0.44（2.27×）"** 来自 **`B40`(4 µm 盒, `N=64`) vs `L0`** ——
与 `B2P_*`（**6 µm 盒, `N=96`, wulff=1, dip=4**）**配置完全不同**
⇒ **那个 0.44 不能当本实验的参照系。**

⇒ 本脚本造**同配置的真对照**：argv 逐条同 `_b2_arm.py`，**只把 `--facet-proj 1` 换成 `0`**，
并**显式传 `--facet-proj-order pre`**（此时该开关无作用，但保证 argv 结构一致）。

**判据**：`比 = steps(B2P_pre) / steps(对照)` 与 `steps(B2P_post) / steps(对照)`。
"""
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
tag = sys.argv[1]

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
    "--facet-proj", "0",                 # ★★ 唯一差别：不开投影
    "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--band-cells", "40",
    "--mob-wulff",
    "--facet-proj-order", "pre",         # 无作用，保证 argv 结构一致
    "--out", "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
    "--tag", tag,
]
cmd = [PY, "-u", "_bk_exp.py"] + argv
print(" ".join(cmd))
sys.exit(subprocess.run(cmd, cwd=FW).returncode)
