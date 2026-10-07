#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_Mtest.py <tag> <M> —— **决定性因果实验**：场数上限 `M` 是否造成"喂成细长"。

## 假设（`R705 §4`，【推理，自洽】）
> **形核事件数（`n_eng_ev`）超过场数上限 `M` ⇒ 新核只能**并入**已有场
> ⇒ 少数几根被持续喂大 ⇒ 细长 ⇒ `f_flat` 高。**

**证据（相关性）**：
| 臂 | `n_eng_ev` | `M` | 事件/M | `nf3` | PCA | `f_flat` |
|---|---:|---:|---:|---:|---:|---:|
| `pre` | **13** | 6 | **2.17** | **2** | **8.03** | **0.1115** ✅ |
| `q0` | **5** | 6 | **0.83** | 5 | 6.95 | 0.0207 |
| `CLIell` | 5 | 6 | 0.83 | 5 | 4.48 | 0.0287 |

## 本实验（**直接操纵 `M`**，且 `--facet-proj 0` ⇒ 与投影解耦）
| 臂 | `M` | 事件/M（预测） | 预测结果 |
|---|---:|---|---|
| **`Mlo3`** | **3** | **≫1** | **`nf3` 低、`f_flat` 高** |
| **`Mhi12`** | **12** | **≪1** | **`nf3` 高、`f_flat` 低** |

## 判据（**先登记，可 FAIL**）
* **C1（单调性）** `nf3(M=3) < nf3(M=6) < nf3(M=12)`
* **C2（`f_flat` 反单调）** `f_flat(M=3) > f_flat(M=6) > f_flat(M=12)`
* **C3（机理直接量）** 事件/M：`M=3` 时 **>1**，`M=12` 时 **<1**
* **★C4（决定性）** 若 `M=3` 给出 **`f_flat ≥ 0.10` 且 步数比 ∈1.0–1.3**
  ⇒ **找到"保面而无动力学代价"的配置**（`B2`/`ell`/`big` 都没做到）

**⚠ 若无单调性 ⇒ 假设被否**（`M` 不是成因）。
"""
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
tag, M = sys.argv[1], sys.argv[2]

# 基线 = `_b2_arm0.py`（= `B2P_q0`），**只改 --laths**（单变量）
argv = [
    "--N", "96", "--dx-nm", "62.5", "--steps", "400",
    "--every", "25", "--snap-every", "25", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--laths", str(M),                     # ★★ 唯一改动
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
    "--facet-proj", "0",                   # ★ 与投影解耦
    "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--band-cells", "40", "--mob-wulff",
    "--out", "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
    "--tag", tag,
]
cmd = [PY, "-u", "_bk_exp.py"] + argv
print(" ".join(cmd))
sys.exit(subprocess.run(cmd, cwd=FW).returncode)
