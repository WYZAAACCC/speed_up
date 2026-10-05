#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g6b_report.py —— 读 G6-b 两臂的 `nuc_dbg.json`，给出**实际变体分布**。"""
import json
import os
import sys

OUT = "/mnt/f/speed_up/_exp/_bk_t5"
tags = sys.argv[1:] or ["g6bA", "g6bB"]
res = {}
for tag in tags:
    p = os.path.join(OUT, "dry_%s" % tag, "nuc_dbg.json")
    print("=" * 88)
    print(f"{tag}   exists={os.path.exists(p)}")
    if not os.path.exists(p):
        continue
    d = json.load(open(p, encoding="utf-8"))
    ev = d.get("T_events", []) or []
    hist, fh = {}, {}
    for e in ev:
        v = int(e.get("variant", -1))
        hist[v] = hist.get(v, 0) + 1
        fh[v] = int(e.get("nfield_of_var", -1))
    print(f"  事件数 = {len(ev)}   末目标 = {d.get('n_target_final')}")
    print(f"  实际变体分布 = {dict(sorted(hist.items()))}")
    print(f"  落在几个变体上 = {len(hist)}")
    print(f"  各变体的静态场数（配额）= {dict(sorted(fh.items()))}")
    print(f"  模式 = {d.get('n_events_by_mode')}")
    res[tag] = dict(n=len(ev), hist=dict(sorted(hist.items())), nvar=len(hist))

print("\n" + "=" * 88)
if len(res) == 2 and all(res.values()):
    a, b = (res[tags[0]], res[tags[1]])
    print(f"事件数      ：{tags[0]}={a['n']}   {tags[1]}={b['n']}   "
          f"=> {'相同' if a['n'] == b['n'] else '**不同**'}")
    print(f"变体分布    ：{'**完全相同**' if a['hist'] == b['hist'] else '**不同**'}")
    print(f"落在几个变体：{tags[0]}={a['nvar']}   {tags[1]}={b['nvar']}   "
          f"=> {'相同' if a['nvar'] == b['nvar'] else '**不同**'}")
    if a['hist'] == b['hist'] and a['n'] == b['n']:
        print("  ⇒ 换 `--laths` 顺序 ⇒ 结果**不变** ⇒ `natural` **不依赖**配额排列 ✓")
    else:
        print("  ⇒ 换 `--laths` 顺序 ⇒ 结果**变了** ⇒ **配额表仍在影响物理**"
              "（`G6` 的缺口成立）")
else:
    print("**某臂无产物 ⇒ 无法判定**")
