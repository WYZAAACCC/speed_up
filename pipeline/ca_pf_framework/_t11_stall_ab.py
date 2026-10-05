#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_stall_ab.py —— **停顿 A/B 判据**（`R623 G5a` 的"是否真的解卡"）。

## 背景（`R623 §13` 与基线实测）
  基线 `dry_t10PRT2_b3`：`nslab_n` 在 **step 20 就到 18，然后 120 步不动**
  （`T_18 = 441.75 K` 远高于 `T_end = 298 K`）⇒ **没走完冷却**。
  我的小冒烟也是"step 1 到 5、然后停"。
  ⇒ 怀疑是 `G5a` 修的那个门控（`fresh` 名额用尽后 `n_fresh ≡ 0`
     ⇒ 唯一的解卡机制被挡在门外）。

## 判据（可 FAIL，两臂只差一个开关 —— 教训 21）
  臂 OFF：`--nuc-resample-ungated 0`（**归档行为**）
  臂 ON ：`--nuc-resample-ungated 1`（`G5a` 的修法）
  其余参数**逐项相同**。

  **判据**：两臂的**末刻 `nslab_n`** 与 **`sites_resampled_ungated`** 计数。
  * 若 ON 臂的 `nslab_n` **继续增长**且 OFF 臂**停住** ⇒ **解卡成立**（`G5a` 有效）；
  * 若两臂都停在同一处 ⇒ 门控**不是**原因 ⇒ 回 ② 重查。
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"

COMMON = [
    "--N", "64", "--dx-nm", "62.5", "--steps", "60", "--every", "10",
    "--snap-every", "99999", "--pair-every", "0", "--norm-smooth", "0",
    "--nthreads", "2", "--grow-stack",
    "--nuc-init", "4", "--nuc-every", "0", "--nuc-law", "athermal",
    "--nuc-block-target", "0", "--nuc-block-parallel", "1",
    "--nuc-supercrit", "1", "--nuc-sites-refill", "1",
    "--qs-clock", "1", "--alpha-km", "0.041739", "--T-end", "298",
    "--cool-rate", "2.3524e6",
    "--nuc-count-mode", "natural", "--per-field-axes", "1",
    "--nuc-order-by-drive", "1",
    "--out", OUT,
]
ARMS = [("stallOFF", "0"), ("stallON", "1")]


def run(tag, ung):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + [
        "--nuc-resample-ungated", ung, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def series(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    if not os.path.exists(p):
        return None
    return list(csv.DictReader(open(p, encoding="utf-8")))


def dbg(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "nuc_dbg.json")
    if not os.path.exists(p):
        return {}
    return (json.load(open(p, encoding="utf-8")).get("dbg", {}) or {})


print("=" * 96)
print("停顿 A/B 判据：`--nuc-resample-ungated` 0 vs 1（其余逐项相同）")
print("=" * 96)
res = {}
for tag, ung in ARMS:
    rc, log = run(tag, ung)
    rows = series(tag)
    d = dbg(tag)
    ns = [r.get("nslab_n") for r in (rows or [])]
    st = [r.get("step") for r in (rows or [])]
    res[tag] = dict(rc=rc, ns=ns, st=st, d=d, log=log)
    print(f"\n[{tag}] ungated={ung}  退出码={rc}")
    print(f"   日志={log}")
    print(f"   step : {st}")
    print(f"   nslab: {ns}")
    print(f"   sites_resampled_ungated = {d.get('sites_resampled_ungated')}")
    print(f"   sites_resampled         = {d.get('sites_resampled')}")
    print(f"   fresh_blocked={d.get('fresh_blocked')}  cov={d.get('cov')}  "
          f"empty={d.get('empty')}  ok={d.get('ok')}")

print("\n" + "=" * 96)
a, b = res["stallOFF"], res["stallON"]
na = next((int(x) for x in reversed(a["ns"] or []) if str(x).strip().isdigit()), None)
nb = next((int(x) for x in reversed(b["ns"] or []) if str(x).strip().isdigit()), None)
print(f"末刻 nslab_n： OFF(归档) = {na}     ON(G5a) = {nb}")
if na is not None and nb is not None:
    if nb > na:
        print(f"   ⇒ ON 臂**继续增长**（+{nb-na}）而 OFF 臂停住 ⇒ **解卡成立** ✅"
              "（`G5a` 在生产形态下有效）")
    elif nb == na:
        print("   ⇒ 两臂停在**同一处** ⇒ **门控不是停顿的原因** ❌"
              " ⇒ 回 ② 重查（别改代码）")
    else:
        print("   ⇒ ON 臂反而更少 ⇒ 异常，必须查")
print(f"★ 可核查串：ON 臂的 `sites_resampled_ungated` = "
      f"{b['d'].get('sites_resampled_ungated')!r}（应 > 0 才说明新路径被走到）")
print("=" * 96)
