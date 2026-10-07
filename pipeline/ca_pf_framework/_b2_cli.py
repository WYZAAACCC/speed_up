#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_cli.py <tag> <mode> —— **纯 CLI 新路线**（`R699 §8`）：不用 `facet_proj`，改激活 `attach` 通道。

## 假设（`R699 §5.3`，【推理】）
`facet_proj` 的"保面"**不是**投影把场修平，而是**步首投影激活了 `attach` 通道**
（`pre` 的 `attach` 11/13、`post`/`q0` 的 `dbg.att=0`）
⇒ **少数板条被喂大** ⇒ 大到能形成平面 ⇒ `f_flat` 高。

**⇒ 若假设成立，则用别的手段激活 `attach` 应能**同时**拿到高 `f_flat` 与 1.0× 动力学。**

## 三个 mode（**纯 CLI，不违反 `R629 E1`**）
| mode | 改动 | 针对 |
|---|---|---|
| `ell` | `--nuc-shape ellipsoid`（现为 `disc`） | 仓库记账："圆盘足迹只有长条板的 1/5" |
| `big` | `--plate-L/W/T 250.0`（现为 125） | 核的初始尺寸 |
| `both` | 两者都改 | — |

## 判据（**先登记，可 FAIL**）
* **①** `f_flat ≥ 0.10`（`BLOCK_SELFAC §9.5`）
* **②** 同 `Vt` 步数比 vs **不开投影**（`B2P_q0`）∈ **1.0–1.3**
* **③** PCA 长:短 **不劣化**（≥ 6.95，即 `q0` 的水平）
* **★ ④（本路线的核心）** **同时**满足 ①② —— 这是 `B2` 做不到的那件事
"""
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
tag, mode = sys.argv[1], sys.argv[2]

# 基线 = `_b2_arm0.py`（= `B2P_q0`：不开投影），逐条同参
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
    "--facet-proj", "0",                 # ★ 不开投影（本路线的前提）
    "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--band-cells", "40", "--mob-wulff",
    "--out", "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
    "--tag", tag,
]

# ---- mode 的改动（**单变量**：一次只改一处）----
if mode in ("ell", "both"):
    i = argv.index("--nuc-shape")
    argv[i + 1] = "ellipsoid"
if mode in ("big", "both"):
    for k in ("--plate-L", "--plate-W", "--plate-T"):
        argv[argv.index(k) + 1] = "250.0"

cmd = [PY, "-u", "_bk_exp.py"] + argv
print(" ".join(cmd))
sys.exit(subprocess.run(cmd, cwd=FW).returncode)
