#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g7_ab.py —— **`G7` 的 A/B**：`--nuc-periodic-seed` 0 vs 1。

## 依据（不是新写的修复，而是**已被论证过、默认关**的开关）
  `windowB_surface.py:2644/2709`（两条 `oob` 拒绝）+ `:3202`（`elong` 越界硬检查）
  + `:3187`（`seed_plate` 最小镜像）**共用同一个 `periodic_seed`**。
  引擎自己的理由（`:2638-2642`）：
    「`cc` 上一步**已经周期折回**，而**动力学也是周期的**
     ⇒ 靠近盒面的位点**与盒心完全等价**，没有理由丢。」
  ⚠ 且注释记：`_r543` 的第一版只改了①+②，T1/T2/T4 全 FAIL 报的正是**第三道闸**
    ⇒ **必须在同一个开关下一起放开**（这正是本 A/B 要验的）。

## `G7` 的取证（已验证，`_t11_g7_report.py`）
  `dbg['oob'] = 2067`，按撞面分类：**z 62.4%** / x 18.2% / y 17.3%
  ⇒ 候选中心全落在 `[0, 0.62) µm` 的**盒壁余量带**、且**全部贴着下界**（`cc.z` 有负值）
  ⇒ **不是"块太大撞壁"**（末态 α′ 只占 `0.558 L` × `0.188 L`）

## 判据（两臂只差一个开关 —— 教训 21）
  * **判据 1**：ON 臂 `dbg['oob']` **显著下降**（期望 → 0 量级）；
  * **判据 2**：ON 臂 `dbg['exc']`（`ValueError` 抛错，含第三道闸）**显著下降**；
  * **判据 3**：ON 臂末刻 `nslab_n` **上升**（这才是用户 ⑧ 要的）；
  * **判据 4**（**反面**）：ON 臂**不得**出现"板条整体贴壁/被截断"——
    用插桩的 `--wrap-every` 查绕盒，**且**用 `region` 量三轴跨度。
  ⚠ 任一判据 FAIL ⇒ 如实记录，**不得**为了让根数上去而放松。
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
    "--nuc-order-by-drive", "0", "--nuc-iface-nucleation", "0",
    # ★ 绕盒监控（判据 4 要它）
    "--wrap-every", "40",
    "--laths", ",".join("1" for _ in range(70)),
    "--out", OUT,
]
ARMS = [("g7OFF", "0"), ("g7ON", "1")]


def run(tag, ps):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + [
        "--nuc-periodic-seed", ps, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def series(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def dbg(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "nuc_dbg.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


print("=" * 98)
print("`G7` A/B：`--nuc-periodic-seed` 0（归档）vs 1（周期最小镜像）")
print("=" * 98)
res = {}
for tag, ps in ARMS:
    rc, log = run(tag, ps)
    rows, j = series(tag), dbg(tag)
    d = j.get("dbg", {}) or {}
    ns = [r.get("nslab_n") for r in rows]
    wrap = [r.get("wrap_any") for r in rows]
    res[tag] = dict(rc=rc, ns=ns, d=d, wrap=wrap, why=j.get("oob_why", {}),
                    geom=j.get("oob_geom", []), log=log)
    print(f"\n[{tag}] periodic_seed={ps}  退出码={rc}")
    print(f"   nslab_n 序列 : {ns}")
    print(f"   oob={d.get('oob')}  exc={d.get('exc')}  cov={d.get('cov')}  "
          f"ok={d.get('ok')}  fresh_blocked={d.get('fresh_blocked')}")
    print(f"   oob 撞面分布 : {dict(sorted((j.get('oob_why') or {}).items()))}")
    print(f"   wrap_any（逐变体绕盒）: {[w for w in wrap if w]}")

print("\n" + "=" * 98)


def lastn(xs):
    return next((int(x) for x in reversed(xs) if str(x).strip().isdigit()), None)


a, b = res["g7OFF"], res["g7ON"]
print("★ 判据汇总")
print(f"  判据1 `oob` : OFF={a['d'].get('oob')}  ON={b['d'].get('oob')}  "
      f"⇒ {'**下降** ✅' if (b['d'].get('oob') or 0) < (a['d'].get('oob') or 0) else '未下降 ❌'}")
print(f"  判据2 `exc` : OFF={a['d'].get('exc')}  ON={b['d'].get('exc')}  "
      f"⇒ {'**下降** ✅' if (b['d'].get('exc') or 0) < (a['d'].get('exc') or 0) else '未下降 ❌'}")
la, lb = lastn(a["ns"]), lastn(b["ns"])
print(f"  判据3 末刻 nslab_n : OFF={la}  ON={lb}  "
      f"⇒ {'**上升** ✅' if (lb or 0) > (la or 0) else '未上升 ❌（如实记录，不放松判据）'}")
w = [x for x in b["wrap"] if x]
print(f"  判据4 绕盒（ON 臂）: {'**检出** ' + str(w) if w else '未检出 ✅'}")
print("=" * 98)
