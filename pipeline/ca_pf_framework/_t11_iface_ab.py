#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_iface_ab.py —— **`G2` 的 A/B**：放开异变体界面形核能否让根数继续增长。

## 背景（`R623 §14` 的实测）
  `_t11_stall_ab.py` 证明：**`G5a` 的门控不是停顿的原因**（两臂都停在 6）。
  日志显示 **所有事件都在同一个温度 T=849 K 发生**，之后 `_tgt = min(N_lath(T), nv)`
  **恒等于 nv** ⇒ 再也触发不了事件。
  基线 `dry_t10PRT2_b3` 的 `18@step20 → 停 120 步` 是同一件事。

## 假设（可 FAIL）
  根数停在 18（基线）是因为**可用的形核通道用尽**：母相被占满后，
  `cov` 守卫只许落在母相（`reg[cover]==0`）⇒ **`fresh`/`stack` 都放不下**
  ⇒ 需要 **`G2`（异变体界面形核）**才能继续。

## 判据（两臂只差一个开关 —— 教训 21）
  臂 OFF：`--nuc-iface-nucleation 0`
  臂 ON ：`--nuc-iface-nucleation 1`
  **nv 必须够大**（否则被 nv 截断，测不出）⇒ 用 `nv >= 2×n(T_end)`。
  两臂**参数相同**、`--steps` 足够长。

  * 判据：末刻 `nslab_n`。ON 臂**显著更高** ⇒ `G2` 是必要的；
  * 且 ON 臂必须有 `iface_ok > 0`（**独有可核查串**）。
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"

# nv 要够大：n(T_end) = 23 ⇒ 给 3 倍余量（也留出多根并存的空间）
COMMON = [
    "--N", "64", "--dx-nm", "62.5", "--steps", "400", "--every", "40",
    "--snap-every", "99999", "--pair-every", "0", "--norm-smooth", "0",
    "--nthreads", "2", "--grow-stack",
    "--nuc-init", "4", "--nuc-every", "0", "--nuc-law", "athermal",
    "--nuc-block-target", "0", "--nuc-block-parallel", "1",
    "--nuc-supercrit", "1", "--nuc-sites-refill", "1",
    "--nuc-resample-ungated", "1",
    "--qs-clock", "1", "--alpha-km", "0.041739", "--T-end", "298",
    "--cool-rate", "2.3524e6",
    "--nuc-count-mode", "natural", "--per-field-axes", "1",
    "--laths", ",".join("1" for _ in range(70)),      # nv=70 ≥ 3×23
    "--out", OUT,
]
ARMS = [("ifaceOFF", "0"), ("ifaceON", "1")]


def run(tag, iface):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + [
        "--nuc-iface-nucleation", iface, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def series(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else None


def dbg(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "nuc_dbg.json")
    return (json.load(open(p, encoding="utf-8")).get("dbg", {}) or {}) \
        if os.path.exists(p) else {}


print("=" * 96)
print("`G2` A/B：放开异变体界面形核（nv=70、steps=400、其余逐项相同）")
print("=" * 96)
res = {}
for tag, iface in ARMS:
    rc, log = run(tag, iface)
    rows = series(tag) or []
    d = dbg(tag)
    ns = [r.get("nslab_n") for r in rows]
    st = [r.get("step") for r in rows]
    res[tag] = dict(rc=rc, ns=ns, st=st, d=d, log=log)
    print(f"\n[{tag}] iface={iface}  退出码={rc}")
    print(f"   step : {st}")
    print(f"   nslab: {ns}")
    print(f"   iface_ok={d.get('iface_ok')} iface_pair={d.get('iface_pair')!r} "
          f"iface_samevar={d.get('iface_samevar')} iface_multi={d.get('iface_multi')}")
    print(f"   ok={d.get('ok')} cov={d.get('cov')} fresh_blocked={d.get('fresh_blocked')} "
          f"empty={d.get('empty')}")

print("\n" + "=" * 96)
a, b = res["ifaceOFF"], res["ifaceON"]


def lastn(rs):
    return next((int(x) for x in reversed(rs) if str(x).strip().isdigit()), None)


na, nb = lastn(a["ns"]), lastn(b["ns"])
print(f"末刻 nslab_n： OFF = {na}    ON = {nb}")
if na is not None and nb is not None:
    if nb > na:
        print(f"   ⇒ ON 臂**更高**（+{nb-na}）⇒ **`G2` 是必要的** ✅"
              "（放开界面形核让根数继续增长）")
    else:
        print("   ⇒ 两臂**相同或更低** ⇒ **`G2` 不是根数不足的原因** ❌ ⇒ 回 ② 重查")
print(f"★ 可核查串：ON 臂 `iface_ok` = {b['d'].get('iface_ok')!r}"
      f"（应 > 0，且 `iface_pair` 形如 '1>2'）")
print("=" * 96)
