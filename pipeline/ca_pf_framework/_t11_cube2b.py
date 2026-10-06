#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cube2.py —— 立方核生长实验 **v2.1**（修 v1 的三处设计缺陷）。

## v1 的缺陷（实测暴露，全部记账）
  1. **核太大 / 盒太小**：500 nm 立方 + 4 µm 盒 ⇒ 200 步后 Vt=32 µm³（涨 325×），
     **step 100 就自贯通** ⇒ 三轴跨度口径失去分辨力；
  2. **漏传 `--grow-stack`** ⇒ 落到 `_bk_exp.py:1909 else:` 分支 ⇒ **播了 6 片**
     （banner 自陈「实际播种 6 片」）；补上后 `nslab=1` ✅；
  3. **没登记碎裂**：引擎把场切成多个连通分量（实测 `nc` 到 15）⇒ 跨度量的是碎片云包络。

## v2.1 的设计
  · **盒 `N=128`（= 8 µm，Δx 仍 62.5 nm，与生产逐字相同）**；
  · **核 250 nm 立方**（4 胞/边）；
  · **240 步 + 每 40 步快照**：v1 实测跨度约 **+13 nm/步**，8 µm 盒的 60% 绕盒线 = 4800 nm
    ⇒ 从 250 nm 起约 350 步撞线 ⇒ 取 240 步以保证**全部读数都在绕盒线内**；
  · **只量场 1**（= `t=0` 播下的那一片；`--grow-stack --nuc-init 0` 保证唯一）。
    ⚠ 引擎的 `stack`/`attach` 通道**仍会加别的场**（`_bk_exp.py:3066` 的 `_ns=1` 恒开）
    ⇒ **不为此改主代码**（`R629 E1`）⇒ 改为**只量场 1**，并在报告里登记"其余场存在"；
  · **臂**：`c2Eq0`（β_h=0，负对照）/ `c2B647`（6.477，生产值）/ `c2B15`（15，由 9:1 反推）。
"""
import glob
import os
import subprocess

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "_exp/_bk_t5"
DX = 62.5e-9
N = 128
CUBE = 250.0
# ★ v2.2 修正（读归档轨迹后）：`dry_t5AB_A` 跑到 **1400 步**才定形
#   ⇒ 240 步太短。按实测速率 ≈13 nm/步、8 µm 盒的 60% 绕盒线 = 4800 nm
#   ⇒ 从 250 nm 起 **1000 步**时跨度约 2.4 µm，**仍在线内** ⇒ 取 1000 步、每 100 步快照。
STEPS = 1000

COMMON = [
    "--N", str(N), "--dx-nm", "62.5", "--steps", str(STEPS),
    "--every", "100", "--snap-every", "100", "--pair-every", "200",
    "--norm-smooth", "0", "--nthreads", "8", "--arm", "dry",
    "--nuc-shape", "disc",
    "--grow-stack",
    "--nuc-every", "0", "--nuc-init", "0",
    "--nuc-law", "cadence", "--nuc-block-target", "0",
    "--gamma0", "0.25", "--gamma-film", "0.6",
    "--alpha-km", "0.041739", "--T-end", "298.0", "--cool-rate", "2352400.0",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--beta-w", "0.0",
    "--ed-eta", "0.253",
    "--mob-iform", "exp2", "--mob-ratio", "9.0", "--mob-dip", "0.0",
    "--facet-proj", "0", "--rank1-swap", "none", "--var-rule", "ed",
    "--nuc-sites-refill", "1",
    "--out", OUT,
]
# ★★★ v2.3（读归档轨迹后新增）：**正对照臂**。
#   实测（`dry_t5AB_B` 场 4）：「伸长在形核后很早就完成」—— 场 4 出生时 L/T 已是 **9.46**，
#   此后 1000 步几乎不变（9.46 → 9.33）；场 2 在 step 320 达峰 8.55 后停滞。
#   ⇒ 若只跑"等轴核"，全 FAIL 也**无法区分**"机制不行"还是"我的装置测不出高长厚比"
#     ⇒ 违反 `P24`（负对照要有分辨力）⇒ **必须加正对照**。
#   ⚠ 尺寸经过**压实测**（`_t11_pos_dry2.py`）：
#     第一版用 `250×250×27.8 nm`（厚 **0.11 格**）⇒ 实测 `nslab=0`、显著分量 **0**、
#     包围跨度仅 **7 nm** ⇒ **量具测不到** ⇒ 放大到 **1250×1250×138.9 nm**
#     （厚 **2.22 格**）⇒ 实测 `nslab=1`、显著分量 **1**、跨度 **136 nm** ✅ 能测。
POS_SIDE = 1250.0
POS_T = POS_SIDE / 9.0        # 138.9 nm ⇒ 核 L/T = 9.00
# ★ v2.4：把 L/T=3 那一档也做成**真的扁核**（对齐 arch3 的核厚），
#   否则"立方核 + beta_h=15"改的是形状而不是伸长（也违反单变量原则）。
CUBE_T_ARCH3 = CUBE / 3.0

ARMS = [("c2Eq0", "0.0"), ("c2B647", "6.477"), ("c2B15", "15.0"),
        ("c2PosA", "6.477"), ("c2Arch3", "6.477")]
# 每个臂的 (plate_L, plate_W, plate_T)：默认 250/250/250 = **立方**
ARMDIM = {"c2PosA": (POS_SIDE, POS_SIDE, POS_T),   # 正对照：核 L/T = 9（1250 nm 级）
          "c2Arch3": (CUBE, CUBE, CUBE_T_ARCH3)}   # 归档式扁核：核 L/T = 3


def run(tag, bh):
    pl, pw, pt = ARMDIM.get(tag, (CUBE, CUBE, CUBE))
    cmd = ([PY, "-u", "_bk_exp.py"] + COMMON
           + ["--plate-L", str(pl), "--plate-W", str(pw), "--plate-T", str(pt),
              "--beta-h", bh, "--tag", tag])
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def ncomp(mask):
    try:
        from scipy import ndimage
        _, n = ndimage.label(mask, structure=np.ones((3, 3, 3)))
        return int(n)
    except Exception:                                  # noqa: BLE001
        return -1


def measure(tag):
    sns = sorted(glob.glob(os.path.join(ROOT, OUT, "dry_%s" % tag, "snap_*.npz")))
    out = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a = np.asarray(z['a_ax'], float)
            w = np.asarray(z['w_ax'], float)
            nh = np.asarray(z['n_hab'], float)
            step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
            NC = reg.shape[0]
        L = NC * DX
        flds = sorted(int(v) for v in np.unique(reg) if v != 0)
        if 1 not in flds:
            out.append((step, 0, None))
            continue
        m = (reg == 1)
        idx = np.argwhere(m).astype(np.float64) * DX
        sa, sw, sn = (float(np.ptp(idx @ a)), float(np.ptp(idx @ w)),
                      float(np.ptp(idx @ nh)))
        out.append((step, len(flds), dict(
            ncell=int(m.sum()), nc=ncomp(m),
            sa=sa, sw=sw, sn=sn,
            ar_lw=sa / max(sw, 1e-30), ar_lt=sa / max(sn, 1e-30),
            wrap=max(sa, sw, sn) > 0.6 * L)))
    return out


print("=" * 104)
print("★ 立方核生长 v2.2: box %.1f um (N=%d), cube %.0f nm, %d steps, every 100"
      % (N * DX * 1e6, N, CUBE, STEPS))
print("=" * 104, flush=True)
for tag, bh in ARMS:
    rc, log = run(tag, bh)
    rows = measure(tag)
    print("\n[%s] beta_h = %s   rc=%d" % (tag, bh, rc), flush=True)
    if not rows:
        print("   **no snapshot**")
        continue
    print("   %-6s %-7s %-8s %-6s %-9s %-9s %-9s %-8s %-8s %s"
          % ('step', 'nfield', 'ncell1', 'nc', 'span_a_nm', 'span_w_nm',
             'span_n_nm', 'L/W', 'L/T', 'wrap'))
    for step, nf, d in rows:
        if d is None:
            print("   %-6d %-7d (field1 absent)" % (step, nf))
            continue
        print("   %-6d %-7d %-8d %-6s %-9.0f %-9.0f %-9.0f %-8.2f %-8.2f %s"
              % (step, nf, d['ncell'], d['nc'] if d['nc'] > 0 else '?',
                 d['sa'] * 1e9, d['sw'] * 1e9, d['sn'] * 1e9,
                 d['ar_lw'], d['ar_lt'], 'WRAP' if d['wrap'] else ''))
