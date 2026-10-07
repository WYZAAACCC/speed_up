#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cube_growth.py —— ★ 用户指定实验：**小盒 + 等长宽高的立方核 ⇒ 看它是否长成板条**。

## 问的是什么
  用户：「在一个小的计算盒子内做一个实验，使用一个小的长宽高相同的核，
         检查其是否会生长成板条状马氏体」。
  ⇒ 这是**把"生长层能否造出板条"单独隔离出来**：核是等轴的（三边相等 ⇒ 无种子偏置），
    若长出来仍是等轴 ⇒ **生长层不产生伸长**（那么"把核预先拉长"就是在代偿生长层）；
    若长出来是板条 ⇒ 生长层本身能造出板条。

## 设计（为什么这样选）
  · **只播一根核**：`--nuc-init 0`（无 fresh 待机位点）+ `--nuc-law cadence` + `--nuc-every 0`
    + 不传 `--grow-stack` ⇒ **无 attach/stack/fresh 任何通道**（`R623` 的验证串：日志应无"形核事件"）。
  · **核是立方**：`--plate-L = --plate-W = --plate-T = 500 nm`（都是一样长）⇒ 等轴。
    ⚠ 记账：**立方核在晶体学上不是真实核形状**（真实 α′ 是 {334} 薄片）；
      本实验是**诊断用探针**（暴露全部界面法向，看哪个方向长得快），**不是"真实形核"的复现**。
  · **小盒**：`N=64 × 62.5 nm = 4 µm`（Δx 与生产**逐字相同** ⇒ 分辨率口径可比；
    内存约 0.2 GB ⇒ 可安全并存）。
  · **各向异性**交给 `--beta-h` / `--beta-w`（= `mob_beta`/`mob_beta_w`，
    `windowB_surface.py:5197/5212` 的 `exp[-β_h(n·n*)² - β_w(n·w)²]`）。
  · **臂**：
      `eq0`  ⇒ `β_h = 0`（**负对照**：无各向异性 ⇒ **必须**长成等轴，否则量具有偏）
      `b647` ⇒ `β_h = 6.477`（**生产值**）
      `b15`  ⇒ `β_h = 15`（≈ 由 Wang 2026 的 9:1 反推值 14.9，`R627 §4`）
  · **判据（可 FAIL）**：
      1. **负对照闸**：`eq0` 臂的终态长厚比必须 ≈ 1（若 ≠ 1 ⇒ 量具/驱动有偏，整批作废）；
      2. **主判据**：`b647`/`b15` 臂的终态**长厚比**是否 `> eq0`（生长层是否造出伸长）；
      3. **靶**：`R627` 唯一可用靶 = 长厚比 **≈9:1**（Wang 2026，Ti-64/LPBF/α′）。
  · **量具**：复用 `_t11_lath_shape_when.py` 的逐场三轴跨度（沿 `a_ax`/`w_ax`/`n_hab`）。
"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"
DX_NM = 62.5
N = 64
CUBE_NM = 500.0          # 立方核边长（三边相同）
STEPS = 600

# 与生产逐字相同的物理开关（取自 `_11` 从 `/proc` 取回的命令行）
COMMON = [
    "--N", str(N), "--dx-nm", str(DX_NM), "--steps", str(STEPS),
    "--every", "50", "--snap-every", "100", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "8",
    "--arm", "dry",
    "--plate-L", str(CUBE_NM), "--plate-W", str(CUBE_NM),
    "--plate-T", str(CUBE_NM),
    "--nuc-shape", "disc",          # 立方（elong=1、along=None ⇒ seed_plate 走圆盘/等轴分支）
    # ★★★ 关键修正：**必须传 `--grow-stack`** 才能"只播第 1 片"
    #   （`_bk_exp.py:1886` 的 `if grow:` 分支走 `_seed_next()` ⇒ 只播 1 片；
    #    而"此后每 --nuc-every 步播下一片"因 `--nuc-every 0` **永不触发**。
    #    ⚠ 我第一版**漏传**它 ⇒ 落到 `:1909 else:` 分支 ⇒ **播了 6 片**（nslab=6、F3面=370）。）
    "--grow-stack",
    "--nuc-every", "0",             # ★ 关驱动层后续播种（配 --grow-stack ⇒ 只有 1 片）
    "--nuc-init", "0",              # ★ 无 fresh 待机位点
    "--nuc-law", "cadence",         # ★ 非 athermal ⇒ 无 athermal 补投
    "--nuc-block-target", "0",      # ★ 无块目标
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739",
    "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-w", "2.3",
    "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "0.0",
    "--facet-proj", "0", "--rank1-swap", "none",
    "--var-rule", "ed", "--nuc-sites-refill", "1",
    "--out", OUT,
]
ARMS = [("cubeEq0", "0.0"), ("cubeB647", "6.477"), ("cubeB15", "15.0")]


def run(tag, bh):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + ["--beta-h", bh, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def measure(tag):
    """逐场量沿 a_ax/w_ax/n_hab 的三轴跨度 ⇒ 长宽比 / 长厚比。"""
    sns = sorted(glob.glob(os.path.join(ROOT, OUT, "dry_%s" % tag, "snap_*.npz")))
    rows = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a = np.asarray(z['a_ax'], float)
            w = np.asarray(z['w_ax'], float)
            nh = np.asarray(z['n_hab'], float)
            step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            Ncell = reg.shape[0]
        L = Ncell * DX_NM * 1e-9
        flds = sorted(int(v) for v in np.unique(reg) if v != 0)
        ar_l, ar_t = [], []
        for k in flds:
            idx = np.argwhere(reg == k).astype(np.float64) * DX_NM * 1e-9
            if idx.shape[0] < 8:
                continue
            sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                          float(np.ptp(idx @ nh)))
            # 长轴取三轴中最大者（立方核无先验长轴）
            trio = sorted([sa, sw, sn], reverse=True)
            ar_l.append(trio[0] / max(trio[1], 1e-30))
            ar_t.append(trio[0] / max(trio[2], 1e-30))
        rows.append((step, len(flds), ar_l, ar_t))
    return rows


print("=" * 100)
print("★ 立方核生长实验：等轴核能否长成板条？（N=%d ⇒ 盒 %.2f µm，Δx=%.1f nm 同生产）"
      % (N, N * DX_NM / 1000.0, DX_NM))
print("=" * 100)
res = {}
for tag, bh in ARMS:
    rc, log = run(tag, bh)
    res[tag] = (bh, rc, log)
    print("  跑完 %-10s β_h=%-7s 退出码=%d  日志=%s" % (tag, bh, rc, log), flush=True)

print("\n" + "=" * 100)
print("逐臂结果（长轴/次长轴 = 长宽比；长轴/最短轴 = 长厚比）")
print("=" * 100)
for tag, (bh, rc, log) in res.items():
    rows = measure(tag)
    print("\n【%s】β_h = %s" % (tag, bh))
    if not rows:
        print("   **无快照** ⇒ 无法判定")
        continue
    print("   %-6s %-6s %-28s %s" % ('step', '场数', '长宽比 中位[范围]', '长厚比 中位[范围]'))
    for step, nf, arl, art in rows:
        def fmt(v):
            return "—" if not v else "%.2f [%.2f, %.2f]" % (
                float(np.median(v)), float(min(v)), float(max(v)))
        print("   %-6d %-6d %-28s %s" % (step, nf, fmt(arl), fmt(art)))
