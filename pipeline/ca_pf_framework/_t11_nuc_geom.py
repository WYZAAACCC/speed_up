#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_nuc_geom.py <tag> —— 算例的**两条播种路径核几何**对照（不含 grep，避免引号坑）。

判据（`R625 §4.6.6`）：
  · **驱动层**（场 1）：`R = plate_W/2`、`elong = plate_L/plate_W`   （`_bk_exp.py:1881`）
  · **引擎**（其余事件）：`R = eng_r_nm`、`elong = eng_elong`        （`_bk_exp.py:2031/2161`）
两者应给**同一个核**（同一物理对象）⇒ 若不等 ⇒ **不一致**。
"""
import json
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
for tag in (sys.argv[1:] or ["dry_t10PROD2"]):
    p = next((os.path.join(b, tag, "meta.json") for b in BASES
              if os.path.exists(os.path.join(b, tag, "meta.json"))), None)
    print("=" * 88)
    if p is None:
        print("【%s】**无 meta.json**" % tag)
        continue
    j = json.load(open(p, encoding="utf-8"))
    a = j.get("exp_args", j)
    g = lambda k, d=None: a.get(k, a.get(k.replace('_', '-'), d))  # noqa: E731

    pl, pw, pt = (float(g('plate_L', 0)), float(g('plate_W', 0)),
                  float(g('plate_T', 0)))
    er, ee = float(g('eng_r_nm', 0)), float(g('eng_elong', 0) or 0)
    print("【%s】" % tag)
    print("  声明板条几何: plate_L=%.0f  plate_W=%.0f  plate_T=%.0f nm"
          % (pl, pw, pt))
    print()
    R_d, e_d = pw / 2.0, (pl / pw if pw else 0)
    print("  ◆ 驱动层（场 1）: R = plate_W/2 = **%.1f nm**  elong = plate_L/plate_W"
          " = **%.2f**  ⇒ 面内长半轴 **%.0f nm**、短半轴 %.0f nm"
          % (R_d, e_d, R_d * e_d, R_d))
    print("  ◆ 引擎（其余事件）: R = eng_r_nm = **%.1f nm**  elong = eng_elong"
          " = **%.2f**  ⇒ 面内长半轴 **%.0f nm**、短半轴 %.0f nm"
          % (er, ee, er * ee, er))
    if R_d and R_d * e_d:
        print()
        print("  ⇒ 面内长半轴之比 = **%.2f×**；短半轴之比 = %.2f×；"
              "椭球体积之比 = **%.2f×**"
              % (er * ee / (R_d * e_d), er / R_d,
                 (er * ee * er * (pt / 2.0)) / (R_d * e_d * R_d * (pt / 2.0))))
        same = abs(er * ee - R_d * e_d) < 1e-9 and abs(er - R_d) < 1e-9
        print("  ⇒ **判定：%s**"
              % ("一致 ✅" if same else
                 "**不一致 ❌**（两条路径造出的核不是同一个几何）"))
    # 引擎核长轴 vs 盒长
    L = j.get('L') or a.get('L')
    N = j.get('N') or a.get('N')
    dx = j.get('dx_nm') or g('dx_nm')
    if L and N:
        Lm = float(L) * 1e6 if float(L) < 1e-3 else float(L)
        print("  盒长 L = %.2f µm ⇒ 引擎核长轴 %.2f µm 占盒长 **%.1f%%**"
              % (Lm, 2 * er * ee / 1000.0, 2 * er * ee / 1000.0 / Lm * 100))
