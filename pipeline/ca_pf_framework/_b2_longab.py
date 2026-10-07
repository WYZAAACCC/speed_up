#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_longab.py —— **B2 的长程 A/B**（`B2-D3` 的三条判据要靠它）。

## 为什么不用 `_t11_facet_arm.py`
那个启动器**没有** `--facet-proj-order` 参数（它只传 `--facet-proj`）
⇒ 直接调 `_bk_exp.py`，把 `C4` 的全套参数照抄，只加 `--facet-proj-order`。

## 配置（= `C4` 的配置，`R675`/`R687` 的对照口径）
`--mob-wulff 1 --mob-dip 4 --facet-proj 1 --band-cells 40 --N 96 --steps 400`
⇒ 盒长 6 µm、`Δx = 62.5 nm`。

## 判据（`B2-D3`，**先登记**）
* **①** `f_flat ≥ 0.10`（在 `post` 臂上）
* **②** 同 `Vt` 步数比 ∈ **1.0–1.3**（`post` vs `pre`；现状 0.44 = 2.27×）
* **③** 长厚比不劣化（`post` 的 PCA 最大 ≥ `pre` 的 95%）

## 用法
  `_b2_longab.py --dry`   只打印将执行的命令
  `_b2_longab.py`         依次跑 pre 与 post
"""
import os
import subprocess
import sys

PY = "/root/miniconda3/envs/ml/bin/python"
FW = "/mnt/f/speed_up/pipeline/ca_pf_framework"
STEPS = "400"

BASE = ["--N", "96", "--steps", STEPS, "--band-cells", "40",
        # ⚠ `--mob-wulff` 是 **store_true 开关（不接收值）** —— 帮助里就是 `[--mob-wulff]`。
        #   ⛔ 我第一版写成 `--mob-wulff 1` ⇒ 那个 `1` 成了多余的 positional
        #      ⇒ `error: unrecognized arguments: 1`（`R694` 记账）。
        "--mob-wulff", "--mob-dip", "4.0",
        "--mob-iform", "exp2", "--mob-ratio", "9.0",
        "--beta-h", "6.477", "--beta-w", "2.3",
        "--facet-proj", "1", "--adv", "proj2",
        "--nuc-mode", "auto", "--eng-cadence", "30"]

DRY = "--dry" in sys.argv
print("=" * 104)
print("B2 长程 A/B —— C4 配置 + `--facet-proj-order pre|post`，%s 步，N=96（6 µm 盒）" % STEPS)
print("=" * 104)
for order in ("pre", "post"):
    tag = "B2L_" + order
    cmd = [PY, "-u", "_bk_exp.py"] + BASE + ["--tag", tag,
                                             "--facet-proj-order", order]
    # ★ 先打印**完整 argv**（不再截断 —— `R694` 的教训：截断的日志让我猜了三轮）
    print("\n  【%s】完整命令（%d 个 token）：" % (order, len(cmd)))
    print("     " + " ".join(cmd))
    if DRY:
        continue
    p = subprocess.run(cmd, cwd=FW)
    print("  ⇒ %s 结束，rc=%d" % (order, p.returncode))
print("\n  ⇒ 两臂跑完后，用 `_t11_vtstep.py`、`_t11_A8_table.py 175` 出判据读数。")
