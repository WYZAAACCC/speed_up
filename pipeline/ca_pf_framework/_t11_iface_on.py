#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_iface_on.py —— **只跑 `ifaceON` 臂**，并与**已停的 `ifaceOFF` 产物**对比。

## 为什么单独写（而不是复用 `_t11_iface_ab.py`）
  `_t11_iface_ab.py` 会**先跑 OFF 再跑 ON** ⇒ **覆盖** `dry_ifaceOFF`
  （那是用户要求"现在就停"时**特意保留**的产物，**不得删改** ——
   本仓库纪律：数据**改名保留、绝不删除**）。
  ⇒ 本脚本**只跑 ON**，OFF 直接读现成的 `series.csv`。

## 参数（与 OFF 逐项相同，只差 `--nuc-iface-nucleation`）
  从 `dry_ifaceOFF/meta.json` 的 `exp_args` **回读**关键参数（硬步骤 A：
  参数取值的唯一权威是算例自己的 meta.json），保证两臂真的只差一个因素。
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"
OFF = os.path.join(OUT, "dry_ifaceOFF")
TAG_ON = "ifaceON"


def read_off():
    p = os.path.join(OFF, "meta.json")
    if not os.path.exists(p):
        sys.exit(f"**找不到 {p}** ⇒ 无法回读参数（OFF 产物必须保留）")
    d = json.load(open(p, encoding="utf-8"))
    return d, (d.get("exp_args", {}) or {})


def read_off_series():
    p = os.path.join(OFF, "series.csv")
    if not os.path.exists(p):
        sys.exit(f"**找不到 {p}**")
    return list(csv.DictReader(open(p, encoding="utf-8")))


meta, ea = read_off()
print("=" * 96)
print("`ifaceON` 臂（只跑这一臂；OFF 读现成产物，不改动）")
print("=" * 96)
print("从 `dry_ifaceOFF/meta.json` 回读的关键参数（硬步骤 A）:")


def g(k, dflt):
    v = ea.get(k, meta.get(k, dflt))
    return dflt if v is None else v


KEYS = [("N", None), ("dx_nm", None), ("steps", None), ("nv", None),
        ("nuc_init", None), ("nuc_every", None), ("nuc_law", None),
        ("nuc_block_target", None), ("nuc_block_parallel", None),
        ("nuc_supercrit", None), ("nuc_sites_refill", None),
        ("nuc_resample_ungated", None), ("qs_clock", None), ("qs_max_relax", None),
        ("alpha_km", None), ("T_end", None), ("cool_rate", None),
        ("nuc_count_mode", None), ("per_field_axes", None),
        ("nuc_order_by_drive", None), ("nuc_iface_nucleation", None)]
for k, _ in KEYS:
    print(f"   {k:24} = {g(k, '(缺)')!r}")

# ---- 用**回读值**构造 ON 臂命令（而不是我手打的常数）----
cmd = [PY, "-u", "_bk_exp.py",
       "--N", str(g("N", 64)), "--dx-nm", str(g("dx_nm", 62.5)),
       "--steps", str(g("steps", 400)), "--every", "40",
       "--snap-every", "99999", "--pair-every", "0",
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
       "--T-end", str(g("T_end", 298)), "--cool-rate", str(g("cool_rate", 2.3524e6)),
       "--nuc-count-mode", str(g("nuc_count_mode", "natural")),
       "--per-field-axes", str(g("per_field_axes", 1)),
       "--nuc-order-by-drive", str(g("nuc_order_by_drive", 1)),
       # ★ **唯一被改的开关**
       "--nuc-iface-nucleation", "1",
       "--laths", ",".join("1" for _ in range(int(g("nv", 70)))),
       "--out", OUT, "--tag", TAG_ON]
print("\nON 臂命令（与 OFF 只差 `--nuc-iface-nucleation 0 → 1`）")
log = "/mnt/f/speed_up/_w2_ifaceON.log"
print(f"   日志 → {log}")
with open(log, "w") as fh:
    rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
print(f"   退出码 = {rc}")

# ---- 对比 ----
off = read_off_series()
pon = os.path.join(OUT, "dry_%s" % TAG_ON, "series.csv")
on = list(csv.DictReader(open(pon, encoding="utf-8"))) if os.path.exists(pon) else []
d_on = {}
pd = os.path.join(OUT, "dry_%s" % TAG_ON, "nuc_dbg.json")
if os.path.exists(pd):
    d_on = json.load(open(pd, encoding="utf-8")).get("dbg", {}) or {}


def col(rows, k):
    return [r.get(k, "") for r in rows]


print("\n" + "=" * 96)
print(f"{'step':>6} | {'OFF nslab':>9} {'OFF Vt':>13} | {'ON nslab':>9} {'ON Vt':>13}")
print("-" * 96)
no, nn = col(off, "nslab_n"), col(on, "nslab_n")
vo, vn = col(off, "Vt"), col(on, "Vt")
for i in range(max(len(no), len(nn))):
    a = no[i] if i < len(no) else ""
    b = nn[i] if i < len(nn) else ""
    va = vo[i] if i < len(vo) else ""
    vb = vn[i] if i < len(vn) else ""
    print(f"{i*40:>6} | {a:>9} {va:>13} | {b:>9} {vb:>13}")


def lastn(xs):
    return next((int(x) for x in reversed(xs) if str(x).strip().isdigit()), None)


la, lb = lastn(no), lastn(nn)
print("\n" + "=" * 96)
print("★ A/B 判据（`G2`：放开异变体界面形核）")
print(f"   OFF 末刻 nslab_n = {la}（step {(len(no)-1)*40}）")
print(f"   ON  末刻 nslab_n = {lb}（step {(len(nn)-1)*40}）")
if la is not None and lb is not None:
    if lb > la:
        print(f"   ⇒ ON **更高**（+{lb-la}）⇒ **`G2` 是必要的** ✅ ——"
              " 放开界面形核让根数继续增长")
    elif lb == la:
        print("   ⇒ 两臂**相同** ⇒ **`G2` 不是根数不足的原因** ❌ ⇒ 回 ② 继续查（不改代码）")
    else:
        print(f"   ⇒ ON **更低**（{lb-la}）⇒ 异常，必须查")
print(f"★ 独有可核查串：ON 臂 `iface_ok` = {d_on.get('iface_ok')!r}"
      f"   `iface_pair` = {d_on.get('iface_pair')!r}"
      f"   `iface_samevar` = {d_on.get('iface_samevar')!r}")
print(f"   （`iface_ok > 0` 才证明**真的走了**新守卫；=0 ⇒ 该判据没分辨力）")
print("=" * 96)
