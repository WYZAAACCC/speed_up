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
import os
import subprocess
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"

tag = sys.argv[1]
wulff = int(sys.argv[2]) if len(sys.argv) > 2 else 0
band = sys.argv[3] if len(sys.argv) > 3 else "20"
bh = sys.argv[4] if len(sys.argv) > 4 else "6.477"      # ★ 物理值 A/B（默认=生产值）
# ★ 步数（默认 300；长跑用 1500）—— `R636 §4`：形状是速度的**时间积分**，
#   以 ~4.5× 的速度比长到 9:1 需约 2900 步 ⇒ 长跑必须显式加步数。
#   ⚠ 记账：第一版把 `STEP` 定义在 `argv` **之后** ⇒ 静默失效（同 `bw` 的坑）；
#     现提到 `argv` 之前，并**显式打印**以便核对（`P44`：要看独有成功串）。
STEP = sys.argv[11] if len(sys.argv) > 11 else "300"
# ★★★ `R642`：**盒尺寸**（`N`）。`R635 §7` 曾测到 `N=128` 用 24 GB ⇒ 放弃 8 µm 盒；
#   但 `_t11_mem_scaling.py` 复测标度：`N=48/64/96` 的构造 RSS = 258/515/1569 MB
#   ⇒ **近似 ∝ N³** ⇒ 外推 `N=128` = **4.02 GB**（不是 24 GB）
#   ⇒ **先前那 24 GB 是多进程并存的测量混淆** ⇒ 8 µm 盒**可行**。
NN = sys.argv[12] if len(sys.argv) > 12 else "64"
dip = sys.argv[5] if len(sys.argv) > 5 else "0.0"       # ★ 45° 凹陷（`R30 §46`：与凸化配套）
iform = sys.argv[6] if len(sys.argv) > 6 else "exp2"    # ★ 面内角函数（`R64 §52`：ellipse ⇒ ratio 恰兑现）
rmode = sys.argv[7] if len(sys.argv) > 7 else ""        # ★ `R634` 重初始化档（'' = 不设 ⇒ sussman）
# ★★★ 2026-10-07 **重大更正**：`--beta-w` 默认改为 **2.3**（仓库设计值）。
#   此前七个臂全用 `0.0` ⇒ **凸化后 `h(a)/h(w)` 被填平成 1.000**（`_t11_wulff_audit.py` 实测）
#   ⇒ **等于在"面内各向异性为零"的配置下测面内各向异性 ⇒ 那七个臂的数据全部作废**。
#   仓库 `_r59_wulff3d.py` 实测（`beta_h=6.477, beta_w=2.3`）：
#     `dip_c=0` ⇒ **3.51**；`dip_c=4` ⇒ **9.73**（与 2D 的 3.45/8.98 一致）✅
bw = sys.argv[8] if len(sys.argv) > 8 else "2.3"
# ★★★ 2026-10-07 **第五个设计缺陷的修法**：核尺寸。
#   4 µm 盒（`N=64`）+ 250 nm 核时，形状会长到 3.4–3.9 µm ⇒ **撞盒**（`R635 §6.4`）
#   而 8 µm 盒在 `nv=220` 下要 **24+ GB**（`R635 §7`）⇒ **不可行**。
#   ⇒ 改为**小核**：125 nm 立方 + 4 µm 盒 ⇒ 形状可长到 ~2.4 µm 仍留余量。
nuc = sys.argv[9] if len(sys.argv) > 9 else "125.0"
# ★★★ 2026-10-07 **第六个设计缺陷的修法**：`--facet-proj`（保面机制）。
#   `windowB_surface.py:4335-4343`（逐字）：
#     「实测平坦端面在界面走过 ~5Δx 就被数值扩散抹掉（f_flat 0.172 → 0.005），
#       而三个来源**全部排除**（平流格式/延拓带宽/再初始化）
#       ⇒ 是"光滑 φ 等值面"表示的**内禀**问题。」
#   ⇒ 这正是 `R637` 独立测到的「oblique 55%、界面粗糙」的根因。
#   算子已过正对照（解析长方体上幂等 s=1.000、体积变化 0.0%）。
#   ⚠ 默认 0（关）；语义 = **每 N 步做一次面片投影**。
fproj = sys.argv[10] if len(sys.argv) > 10 else "0"

argv = [
    PY, "-u", "_bk_exp.py",
    "--N", NN, "--dx-nm", "62.5", "--steps", STEP,
    "--every", "25", "--snap-every", "25", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "4", "--arm", "dry",
    "--plate-L", nuc, "--plate-W", nuc, "--plate-T", nuc,
    "--nuc-shape", "disc", "--grow-stack",
    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-h", bh, "--beta-w", bw, "--ed-eta", "0.253",
    "--mob-iform", iform, "--mob-ratio", "9.0", "--mob-dip", dip,
    "--facet-proj", fproj, "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--band-cells", band,
    "--out", OUT, "--tag", tag,
]
if wulff:
    argv.append("--mob-wulff")
log = "/mnt/f/speed_up/_w2_%s.log" % tag
env = dict(os.environ)
if rmode:
    env['REINIT_MODE'] = rmode            # ★ `R634`：重初始化档（不设 ⇒ 默认 sussman）
    print("tag=%s  mob_wulff=%d  dip=%s  iform=%s  **REINIT_MODE=%s**"
          "  beta_w=%s  facet_proj=%s  steps=%s"
          % (tag, wulff, dip, iform, rmode, bw, fproj, STEP), flush=True)
else:
    print("tag=%s  mob_wulff=%d  dip=%s  iform=%s  REINIT_MODE=(默认 sussman)"
          "  beta_w=%s  facet_proj=%s  steps=%s"
          % (tag, wulff, dip, iform, bw, fproj, STEP), flush=True)
with open(log, "w") as fh:
    rc = subprocess.call(argv, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, env=env)
print("退出码 = %d  日志=%s" % (rc, log))
