#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g7_report.py —— 读 `oob_geom` / `oob_why`，给出 **G7（落位越界）** 的几何判读。

## 要回答（可 FAIL）
  越界的候选落点**撞的是哪几个面**？`cc` 落在盒内还是盒外？离壁多远？
  据此判断修法方向：
    * 若绝大多数撞**同一个面**、且 `cc` 落在盒外不远处
      ⇒ 是**落位搜索的方向问题**（一直在同一侧往外推）⇒ 让搜索**换方向/换面内空位**；
    * 若 `cc` 在盒**内**却被拒 ⇒ 是**判据过严**（`R + 0.3 µm` 的余量）⇒ 改判据；
    * 若均匀撞多个面 ⇒ 是**盒子确实满了** ⇒ 只能改 `nv`/`L`/`t`（物理参数）。
"""
import json
import os
import sys
from collections import Counter

BASES = ["/mnt/f/speed_up/_exp/_bk_t5",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]
tags = sys.argv[1:] or ["ifaceON", "ifaceOFF"]
for tag in tags:
    d = next((os.path.join(b, "dry_%s" % tag) for b in BASES
              if os.path.isdir(os.path.join(b, "dry_%s" % tag))), None)
    print("=" * 96)
    print(f"【{tag}】  dir={d}")
    if d is None:
        print("  **目录不存在**")
        continue
    p = os.path.join(d, "nuc_dbg.json")
    if not os.path.exists(p):
        print("  **无 nuc_dbg.json**（跑完才写）")
        continue
    j = json.load(open(p, encoding="utf-8"))
    dbg = j.get("dbg", {}) or {}
    geom = j.get("oob_geom", []) or []
    why = j.get("oob_why", {}) or {}
    print(f"  `dbg['oob']`（越界总次数，**引擎计数**） = {dbg.get('oob')}")
    print(f"  记录到的落点条数 = {len(geom)}（**只保留前 24 条**，纯记录）")
    print(f"  按撞面分类（`oob_why`） = {dict(sorted(why.items()))}")
    if why:
        tot = sum(why.values())
        for k, v in sorted(why.items(), key=lambda x: -x[1]):
            print(f"    撞面 {k:>5} : {v:6d} 次 （{100.0*v/tot:5.1f}%）")
    if not geom:
        print("  ⚠ **没有落点记录** ⇒ 该跑用的是**未插桩**的代码，或没发生越界")
        print("     ⇒ 要拿到几何判读，需用插桩后的代码重跑该臂（或只跑一小段）。")
        continue
    print(f"\n  前 {len(geom)} 条落点（µm）:")
    print(f"    {'why':>7} {'face':>5} {'cc.x':>8} {'cc.y':>8} {'cc.z':>8} "
          f"{'R(nm)':>6} {'L(µm)':>7}  头/尾")
    for g in geom:
        cc = g.get("cc") or [None] * 3
        print(f"    {str(g.get('why')):>7} {str(g.get('face')):>5} "
              f"{cc[0]:>8.3f} {cc[1]:>8.3f} {cc[2]:>8.3f} "
              f"{g.get('R_nm'):>6} {g.get('L_um'):>7}")
    # 判读
    L = geom[0].get("L_um") or 4.0
    R = (geom[0].get("R_nm") or 320.0) / 1000.0
    lo, hi = R + 0.3, L - R - 0.3
    print(f"\n  ★ 判据用阈值（引擎式 `cc < R+0.3µm` 或 `cc > L−R−0.3µm`）："
          f"合法区间 = [{lo:.3f}, {hi:.3f}] µm（L={L} µm, R={R:.3f} µm）")
    inside = sum(1 for g in geom
                 if all(lo <= v <= hi for v in (g.get("cc") or [0, 0, 0])))
    print(f"    落点在**合法区间内**却仍被拒的条数 = {inside} / {len(geom)}")
    faces = Counter(g.get("face") for g in geom)
    print(f"    撞面分布（前 24 条）= {dict(faces)}")
    print("  ⇒ 判读：撞面**高度集中** ⇒ 落位搜索的方向问题；"
          "撞面**分散** ⇒ 盒子真的满了。")
print("=" * 96)
