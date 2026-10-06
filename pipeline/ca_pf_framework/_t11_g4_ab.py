#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g4_ab.py —— **补做 `G4` 的验证**（`R625 §1.2` 记的唯一「存在，未验证」项）。

## 背景
  `R625` 的独有串核对表显示：`--per-field-axes` **从未被任何算例开启**
  ⇒ 按硬步骤 D 只能写「**存在，未验证**」。
  ⇒ 本脚本用一个**极小盒**（`N=32`、`nv=12`、80 步、~300 MB）把这一项补成"已验证"。

## 判据（可 FAIL，两臂只差一个开关）
  1. **ON 臂必须出现 `G3 PASS` 独有串**（`G3` 的逐变体长轴自检）；
  2. **ON 臂必须出现逐变体轴相关的运行期输出**（`_variant_axes` / 逐变体轴）；
  3. **OFF 臂必须两串都不出现**（⇒ 开关真的门控住，不是"恒开"）；
  4. **两臂形态量必须有可测差异**（否则该开关对本量级无影响 ⇒ 如实记录）。
"""
import csv
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"

COMMON = [
    "--N", "32", "--dx-nm", "62.5", "--steps", "80", "--every", "40",
    "--snap-every", "80", "--pair-every", "40", "--norm-smooth", "0",
    "--nthreads", "2", "--grow-stack",
    "--nuc-init", "3", "--nuc-every", "0", "--nuc-law", "athermal",
    "--nuc-block-target", "2", "--nuc-block-parallel", "1",
    "--nuc-supercrit", "1", "--nuc-sites-refill", "1",
    "--nuc-periodic-seed", "1", "--nuc-shape", "ellipsoid",
    "--qs-clock", "1", "--qs-max-relax", "100",
    "--alpha-km", "0.041739", "--T-end", "298", "--cool-rate", "2.3524e6",
    "--plate-L", "1000", "--plate-W", "500", "--plate-T", "510",
    "--gamma0", "0.25", "--beta-h", "6.477",
    # 2 个变体 × 6 个场 = nv 12（**至少 2 个变体**，否则"逐变体轴"无意义）
    "--laths", ",".join(str(v) for v in (1, 2) for _ in range(6)),
    "--out", OUT,
]
ARMS = [("g4OFF", "0"), ("g4ON", "1")]


def run(tag, pfa):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + ["--per-field-axes", pfa,
                                               "--tag", tag]
    log = "/mnt/f/speed_up/_w2_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def grab(log, pat):
    try:
        return [ln.rstrip() for ln in open(log, encoding="utf-8",
                                           errors="replace") if pat in ln]
    except OSError:
        return []


def rows(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "series.csv")
    return list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []


print("=" * 98)
print("`G4` 补验证：`--per-field-axes` 0 vs 1（N=32, nv=12, 80 步）")
print("=" * 98)
res = {}
for tag, pfa in ARMS:
    rc, log = run(tag, pfa)
    g3 = grab(log, 'G3 PASS') + grab(log, 'along·nrm') + grab(log, 'along_per_variant')
    ax = grab(log, 'per-field-axes') + grab(log, '_variant_axes') + grab(log, '逐变体轴')
    rr = rows(tag)
    res[tag] = dict(rc=rc, g3=g3, ax=ax, rows=rr, log=log)
    print(f"\n[{tag}]  per-field-axes={pfa}  退出码={rc}")
    print(f"   `G3` 串命中 = {len(g3)}   `逐变体轴` 串命中 = {len(ax)}")
    for ln in (g3 + ax)[:4]:
        print("     ★ " + ln.strip()[:130])
    if rr:
        print(f"   末行: step={rr[-1].get('step')} nslab_n={rr[-1].get('nslab_n')} "
              f"Vt={rr[-1].get('Vt')}")

print("\n" + "=" * 98)
print("★ 判据汇总")
a, b = res["g4OFF"], res["g4ON"]
c1 = len(b['g3']) > 0
c2 = len(b['ax']) > 0
c3 = (len(a['g3']) == 0) and (len(a['ax']) == 0)
print(f"  判据1 ON 臂出 `G3 PASS`        : {'✅' if c1 else '❌ 未出'}")
print(f"  判据2 ON 臂出逐变体轴输出      : {'✅' if c2 else '❌ 未出'}")
print(f"  判据3 OFF 臂两串皆无（门控住）  : {'✅' if c3 else '❌ 恒开'}")
if a['rows'] and b['rows']:
    ra, rb = a['rows'][-1], b['rows'][-1]
    d = (ra.get('nslab_n') != rb.get('nslab_n')) or (ra.get('Vt') != rb.get('Vt'))
    print(f"  判据4 两臂形态量有差异        : "
          f"{'✅ nslab_n %s vs %s, Vt %s vs %s' % (ra.get('nslab_n'), rb.get('nslab_n'), ra.get('Vt'), rb.get('Vt')) if d else '⚠ **无差异**（如实记录）'}")
print("=" * 98)
