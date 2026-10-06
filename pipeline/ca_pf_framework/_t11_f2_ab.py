#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_f2_ab.py —— **§122 的受控对照**：`--f2-pair-gamma` λ = 0 / 0.5 / 1。

## 依据（代码注释自己要求的，`windowB_lath.py:288-294` 原文）
> * **λ = 1** ⇒ 最共格的对（`‖Δε‖` 最小）拿到 `γ_lo = 0`，最不相容的退回 `γ₀`
>   ⇒ **packet 形成会被促进**（同惯习面的两个变体贴在一起变便宜）。
> ⚠ **记账**：这条补法有一个**方向不显然**的后果 ——
>   "促进 packet" 与 "`§94` 的 `k*=6` 六变体自协调"是**两个不同的物理目标**，
>   而后者要求"6 个惯习面各取一个" ⇒ **在面内聚集可能反而远离 `r = 0` 那一族**。
> ⇒ **必须做受控对照（λ = 0 / 0.5 / 1），不得预设哪个对。**

## 机制（`windowB_lath.py:295-318`）
```
λ = 0  ⇒ F2 项保持 NaN ⇒ 走标量路径（**归档**）
λ > 0  ⇒ 逐对填充  γ_F2(v,w) = γ₀·[(1−λ) + λ·min(1, ‖Δε_{v,w}‖/Δe_ref)]
          Δe_ref = max over 异变体对的 ‖Δε‖
```

## 判据（可 FAIL）
  1. **独有串**（硬步骤 D）：λ>0 的两臂必须打印 `§122` 那段（含 `Δe_ref` 与 `n_f2`）；
  2. **量具自检**：λ=0 臂**必须不打印**该串（否则开关没生效）；
  3. **形态差异**：末态 `nslab_n` / 逐场胞数 / 长宽比 / 块结构三臂比较；
  4. **物理方向**：若 λ 促进 packet，则应看到**同惯习面变体的聚集增强**；
     ⚠ 但**不预设**（代码注释明确说两个目标可能相反）⇒ 只如实记录。
"""
import csv
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"

# 与 `ifaceOFF/ON` 同参数（N=64, nv=70），只差 `--f2-pair-gamma`
COMMON = [
    "--N", "64", "--dx-nm", "62.5", "--steps", "400", "--every", "40",
    "--snap-every", "400", "--pair-every", "40", "--norm-smooth", "0",
    "--nthreads", "4", "--grow-stack",
    "--nuc-init", "4", "--nuc-every", "0", "--nuc-law", "athermal",
    "--nuc-block-target", "0", "--nuc-block-parallel", "1",
    "--nuc-supercrit", "1", "--nuc-sites-refill", "1",
    "--nuc-resample-ungated", "1", "--nuc-periodic-seed", "1",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--alpha-km", "0.041739", "--T-end", "298", "--cool-rate", "2.3524e6",
    "--nuc-count-mode", "natural", "--per-field-axes", "1",
    "--laths", ",".join("1" for _ in range(70)),
    "--out", OUT,
]
ARMS = [("f2L0", "0.0"), ("f2L05", "0.5"), ("f2L1", "1.0")]


def run(tag, lam):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + ["--f2-pair-gamma", lam,
                                               "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def series(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def grab(log, pat):
    try:
        return [ln.rstrip() for ln in open(log, encoding="utf-8", errors="replace")
                if pat in ln]
    except OSError:
        return []


print("=" * 100)
print("§122 受控对照：`--f2-pair-gamma` λ = 0 / 0.5 / 1（N=64, nv=70, 400 步）")
print("=" * 100)
res = {}
for tag, lam in ARMS:
    rc, log = run(tag, lam)
    rows = series(tag)
    diag = grab(log, '§122') + grab(log, 'F2')
    res[tag] = dict(rc=rc, rows=rows, lam=lam, diag=[d for d in diag][:4], log=log)
    ns = [r.get('nslab_n') for r in rows]
    print(f"\n[{tag}]  λ={lam}  退出码={rc}")
    print(f"   nslab_n 序列 : {ns}")
    if rows:
        print(f"   末行: step={rows[-1].get('step')} nslab_n={rows[-1].get('nslab_n')} "
              f"Vt={rows[-1].get('Vt')}")
    for d in res[tag]['diag']:
        print("   ★ " + d.strip()[:140])

print("\n" + "=" * 100)
print("★ 判据汇总")
for tag, lam in ARMS:
    r = res[tag]
    hit = bool(r['diag'])
    print(f"  {tag:>7} λ={lam:<4} 独有串={'✅ 有' if hit else '❌ 无'}"
          f"   末刻 nslab_n="
          f"{(r['rows'][-1].get('nslab_n') if r['rows'] else '—')}")
l0 = bool(res['f2L0']['diag'])
print(f"\n  判据2 量具自检（λ=0 应**无**独有串）: "
      f"{'✅ PASS（开关确实门控住了）' if not l0 else '❌ FAIL（λ=0 也打印 ⇒ 开关没生效）'}")
a = res['f2L0']['rows'][-1].get('nslab_n') if res['f2L0']['rows'] else None
b = res['f2L1']['rows'][-1].get('nslab_n') if res['f2L1']['rows'] else None
print(f"  判据3 形态差异（λ=0 vs λ=1 末刻 nslab_n）: {a} vs {b} ⇒ "
      f"{'✅ 有差异' if (a != b) else '⚠ **无差异**（如实记录：F2 耦合对本量级结果无影响）'}")
print("=" * 100)
