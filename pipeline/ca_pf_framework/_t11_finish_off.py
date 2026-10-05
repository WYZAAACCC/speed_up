#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_finish_off.py —— 把 `ifaceOFF` **跑到 400 步**（补齐那 80 步），并做前后一致性核对。

## 为什么要重跑（而不是续跑）
  `ifaceOFF` 在 step 320 被用户要求停下，而**那次跑没开 `--ckpt-every`**
  ⇒ 目录里**没有 `ckpt/`** ⇒ `--resume` **用不了**（`_bk_exp.py:2534` 会
  `SystemExit('目录里没有可用的检查点')`）。
  ⇒ 只能**同参数重跑**。动力学是确定性的 ⇒ 前 320 步应与旧产物**一致**
  （本脚本会**核对**这一点，作为重跑可信的判据）。

## 安全（数据绝不删除）
  旧 `series.csv` **改名归档**为 `series_partial_step<N>_<时间戳>.csv`，
  再让新跑写新的 `series.csv`。**一个字都不删。**

## 判据（可 FAIL）
  1. 新跑必须**走完 400 步**（`closure.json` + `snap_00400.npz` 存在）；
  2. **重跑一致性**：新产物在 step ≤ 320 的 `nslab_n` / `Vt` 必须与**旧归档**
     **逐行相同**（确定性判据；不同 ⇒ 说明有随机性/我漏了参数 ⇒ 必须查）；
  3. 补齐段（320→400）的 `nslab_n` 读数落盘。
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"
OFF = os.path.join(OUT, "dry_ifaceOFF")
TAG = "ifaceOFF"


def read_meta():
    p = os.path.join(OFF, "meta.json")
    if not os.path.exists(p):
        sys.exit(f"**找不到 {p}**")
    d = json.load(open(p, encoding="utf-8"))
    return d, (d.get("exp_args", {}) or {})


meta, ea = read_meta()


def g(k, dflt=None):
    v = ea.get(k, meta.get(k, dflt))
    return dflt if v is None else v


# ---- ① 归档旧 series.csv（改名，不删）----
old_series = os.path.join(OFF, "series.csv")
old_rows = []
if os.path.exists(old_series):
    old_rows = list(csv.DictReader(open(old_series, encoding="utf-8")))
    nlast = old_rows[-1].get("step", "?") if old_rows else "?"
    sup = os.path.join(OFF, "series_partial_step%s_%s.csv"
                       % (nlast, time.strftime("%Y%m%d_%H%M%S")))
    shutil.move(old_series, sup)
    print(f"① 旧 series.csv（{len(old_rows)} 行，末 step={nlast}）"
          f"**已改名归档** → {os.path.basename(sup)}")
else:
    print("① 没有旧 series.csv（无需归档）")

# ---- ② 构造与元数据逐项一致的重跑命令 ----
cmd = [PY, "-u", "_bk_exp.py",
       "--N", str(g("N", 64)), "--dx-nm", str(g("dx_nm", 62.5)),
       "--steps", "400", "--every", "40",
       "--snap-every", str(g("snap_every", 99999)),
       "--pair-every", str(g("pair_every", 0)),
       "--norm-smooth", str(g("norm_smooth", 0)),
       "--nthreads", str(g("nthreads", 2)), "--grow-stack",
       "--nuc-init", str(g("nuc_init", 4)), "--nuc-every", str(g("nuc_every", 0)),
       "--nuc-law", str(g("nuc_law", "athermal")),
       "--nuc-block-target", str(g("nuc_block_target", 0)),
       "--nuc-block-parallel", str(g("nuc_block_parallel", 1)),
       "--nuc-supercrit", str(g("nuc_supercrit", 1)),
       "--nuc-sites-refill", str(g("nuc_sites_refill", 1)),
       "--nuc-resample-ungated", str(g("nuc_resample_ungated", 1)),
       "--qs-clock", str(g("qs_clock", 1)),
       "--alpha-km", str(g("alpha_km", 0.041739)),
       "--T-end", str(g("T_end", 298)),
       "--cool-rate", str(g("cool_rate", 2.3524e6)),
       "--nuc-count-mode", str(g("nuc_count_mode", "natural")),
       "--per-field-axes", str(g("per_field_axes", 1)),
       "--nuc-order-by-drive", str(g("nuc_order_by_drive", 0)),
       "--nuc-iface-nucleation", "0",          # ★ 归档行为臂
       "--laths", ",".join("1" for _ in range(int(g("nv", 70)))),
       "--out", OUT, "--tag", TAG]
log = "/mnt/f/speed_up/_w2_ifaceOFF_rerun.log"
print(f"\n② 重跑（参数从 meta.json 的 exp_args 回读）  日志 → {log}")
with open(log, "w") as fh:
    rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print(f"   退出码 = {rc}")

# ---- ③ 判据 ----
print("\n" + "=" * 92)
new_series = os.path.join(OFF, "series.csv")
new_rows = list(csv.DictReader(open(new_series, encoding="utf-8"))) \
    if os.path.exists(new_series) else []
print(f"③ 判据 1：走完 400 步？")
for f in ("closure.json", "nuc_dbg.json", "snap_00400.npz"):
    p = os.path.join(OFF, f)
    print(f"   {f:20} {'✅ 存在' if os.path.exists(p) else '❌ **缺失**'}")
print(f"   新 series.csv 行数 = {len(new_rows)}（末 step="
      f"{new_rows[-1].get('step') if new_rows else '?'}）")

print(f"\n③ 判据 2：重跑一致性（step ≤ 旧末步 的行必须逐行相同）")
common = min(len(old_rows), len(new_rows))
diff = []
for i in range(common):
    for k in ("step", "nslab_n", "Vt"):
        a, b = old_rows[i].get(k), new_rows[i].get(k)
        if a != b:
            diff.append((i, k, a, b))
print(f"   比较了 {common} 行 × 3 列（step/nslab_n/Vt）")
if not diff:
    print("   ⇒ ✅ **逐行相同** ⇒ 重跑可复现（确定性成立），补齐段可信")
else:
    print(f"   ⇒ ❌ **{len(diff)} 处不同** ⇒ 必须查（有随机性？漏了参数？）")
    for i, k, a, b in diff[:8]:
        print(f"      行{i} {k}: 旧={a!r} 新={b!r}")

print(f"\n③ 补齐段（旧末步之后）的读数：")
for r in new_rows[common:]:
    print(f"   step {r.get('step'):>4}  nslab_n = {r.get('nslab_n'):>4}  "
          f"Vt = {r.get('Vt')}")
if new_rows:
    last = new_rows[-1]
    print(f"\n★ `ifaceOFF` 终点（step {last.get('step')}）："
          f"nslab_n = **{last.get('nslab_n')}**   Vt = {last.get('Vt')}")
    print("   （与 `ifaceON` 的 8 比较 ⇒ 见 §14.4）")
print("=" * 92)
