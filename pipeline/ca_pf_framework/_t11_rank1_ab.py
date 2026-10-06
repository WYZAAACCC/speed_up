#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_rank1_ab.py —— **②-9 的受控对照**：`--rank1-swap none` vs `invariant`。

## 依据（用户既有裁定，`_bk_exp.py:913-920` 的注释原文）
  「`NPF[v]=argmin_normal(C,ε)` 是**弹性能极小法向**，**不是**晶体学惯习面；
    按**不变平面（IPS）判据**，`V1/V3/V8` 应当用 `a` 而**不是** `NPF`（两者差 **82°**）
    ⇒ **用户裁定：两条都跑，作受控对照**。」
  而 `--rank1-swap` **默认 `none` ⇒ 这条裁定从未执行**（`R619` ②-9）。

## 机制（`_bk_exp.py:1060-1097`，已读全）
  `rB(u) = ‖(F−I)·B_u‖₂`（`B_u` = 平面 ⟂u 内的一组基）—— "**平面 ⟂u 内的向量经 F 后
  是否留在该平面内**"；不变平面法向 = 使 `rB` 最小的 `u`。
  判据：若 `rB(F, a) < rB(F, NPF)` ⇒ 该变体的 `NPF` **不是**不变平面法向 ⇒ **对调 `n*` 与 `a`**。
  ★ **内建正对照**：合成 IPS `F = I + 0.2·d pᵀ` 上必须选中 `p`，否则直接 `SystemExit`
    ⇒ 这条判据**自带分辨力证明**。

## 判据（可 FAIL，两臂只差一个开关 —— 教训 21）
  1. **ON 臂必须打印受影响变体清单**（独有串 `选支受控对照`），且**正对照 PASS**；
  2. 两臂的**末态形态量**（`nslab_n` / 长宽比 / 绕盒）**应有可测差异** ——
     若无差异 ⇒ 说明该对调对结果无影响（也是一个有意义的结论，**如实记录**）；
  3. **归档不变**：`none` 臂（默认）必须与既有归档一致（本脚本只跑，不改代码）。

⚠ 盒子取 `N=48`（`L=3 µm`）：板条 `elong*R=1.2 µm` 需 `margin>1.2 µm` ⇒ `L/2=1.5 µm` 够。
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
    "--N", "48", "--dx-nm", "62.5", "--steps", "160", "--every", "40",
    "--snap-every", "160", "--pair-every", "40", "--norm-smooth", "0",
    "--nthreads", "4", "--grow-stack",
    "--nuc-init", "3", "--nuc-every", "0", "--nuc-law", "athermal",
    "--nuc-block-target", "2", "--nuc-block-parallel", "1",
    "--nuc-supercrit", "1", "--nuc-sites-refill", "1",
    "--nuc-periodic-seed", "1", "--nuc-shape", "ellipsoid",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--alpha-km", "0.041739", "--T-end", "298", "--cool-rate", "2.3524e6",
    "--plate-L", "1000", "--plate-W", "500", "--plate-T", "510",
    "--gamma0", "0.25", "--beta-h", "6.477",
    # ⚠ **不要传 `--mob`** —— `MOB` 是**模块级常量**（`_bk_exp.py:48` 从
    #   `T16_verify_rve` 导入），**不是 CLI 参数**（我第一版传了 ⇒ argparse 会拒）。
    # nv=30（3 个变体 × 10 个场）—— 小盒够用、跑得快
    "--laths", ",".join(str(v) for v in (1, 2, 3) for _ in range(10)),
    "--out", OUT,
]
ARMS = [("r1none", "none"), ("r1inv", "invariant")]


def run(tag, swap):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + ["--rank1-swap", swap, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def series(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


def grab(log, pat):
    out = []
    try:
        for ln in open(log, encoding="utf-8", errors="replace"):
            if pat in ln:
                out.append(ln.rstrip())
    except OSError:
        pass
    return out


print("=" * 98)
print("②-9 受控对照：`--rank1-swap none` vs `invariant`（N=48, nv=30, 160 步）")
print("=" * 98)
res = {}
for tag, sw in ARMS:
    rc, log = run(tag, sw)
    rows = series(tag)
    # 独有串：受影响变体清单 + 正对照
    hits = grab(log, '选支受控对照') + grab(log, '受影响变体')
    pos = [ln for ln in grab(log, '正对照') if 'PASS' in ln or '失败' in ln]
    res[tag] = dict(rc=rc, rows=rows, hits=hits[:3], pos=pos[:2], log=log)
    print(f"\n[{tag}]  swap={sw}  退出码={rc}")
    for ln in res[tag]['hits']:
        print("   " + ln.strip()[:150])
    for ln in res[tag]['pos']:
        print("   " + ln.strip()[:150])
    if rows:
        print(f"   末行: step={rows[-1].get('step')} nslab_n={rows[-1].get('nslab_n')} "
              f"Vt={rows[-1].get('Vt')}")

print("\n" + "=" * 98)
a, b = res["r1none"], res["r1inv"]
print("★ 判据汇总")
_ok1 = bool(b['pos']) and any('PASS' in x for x in b['pos'])
print(f"  判据1 正对照 PASS（ON 臂）        : {'✅' if _ok1 else '❌（或该臂无输出 ⇒ 未跑成）'}")
print(f"  判据1b 受影响变体清单（ON 臂）     : "
      f"{'✅ ' + str(len(b['hits'])) + ' 行' if b['hits'] else '❌ 无（⇒ 判据没走到）'}")
for tag, r in (("none", a), ("invariant", b)):
    last = r['rows'][-1] if r['rows'] else {}
    print(f"  末态 {tag:>9}: nslab_n={last.get('nslab_n')}  Vt={last.get('Vt')}")
if a['rows'] and b['rows']:
    la, lb = a['rows'][-1].get('nslab_n'), b['rows'][-1].get('nslab_n')
    print(f"  判据2 形态是否有差异              : "
          f"{'✅ 有（nslab_n %s vs %s）' % (la, lb) if la != lb else '⚠ 无差异（如实记录：该对调对结果无影响）'}")
else:
    print("  判据2：**某臂无 series.csv ⇒ 未能比较**")
print("=" * 98)
