#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_blk_hist.py —— 读某算例 `series.csv` 里**有块列的那些行**（块表只在 `--pair-every` 命中时算）。

用法: _t11_blk_hist.py <tag> [最多打印几行]
"""
import csv
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
tag = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PRT2_b3_1005_1213"
nshow = int(sys.argv[2]) if len(sys.argv) > 2 else 12

d = next((os.path.join(b, tag) for b in BASES if os.path.isdir(os.path.join(b, tag))), None)
if d is None:
    sys.exit(f"找不到 {tag}")
p = os.path.join(d, "series.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print(f"{p}\n共 {len(rows)} 行")

KEYS = ["step", "nslab_n", "nslab_nu", "nblk_sig", "blk_laths", "n_var_sig",
        "Vt", "n_lath", "长nm" if "长nm" in rows[0] else "nf3_col"]
have = [k for k in KEYS if k in rows[0]]
print(f"可用列: {have}\n")

withblk = [r for r in rows if (r.get("nblk_sig") or "").strip() not in ("", "nan")]
print(f"有 `nblk_sig` 的行数 = {len(withblk)}")
if withblk:
    print("\n" + " | ".join(f"{k:>10}" for k in have))
    for r in withblk[-nshow:]:
        print(" | ".join(f"{str(r.get(k,''))[:10]:>10}" for k in have))
    # 末次块表的每块根数
    last = withblk[-1]
    print(f"\n★ 末次块表（step={last.get('step')}）：")
    print(f"   nblk_sig  = {last.get('nblk_sig')}")
    print(f"   blk_laths = {last.get('blk_laths')}")
    print(f"   n_var_sig = {last.get('n_var_sig')}")
    try:
        bl = [int(x) for x in str(last.get("blk_laths", "")).replace("/", ",").split(",")
              if x.strip().isdigit()]
        nb = int(float(last.get("nblk_sig")))
        if bl and nb:
            print(f"   ⇒ 块数={nb}  根数合计={sum(bl)}  **每块平均 = {sum(bl)/nb:.2f}**")
            print(f"   ⇒ 块内根数分布 = {sorted(bl, reverse=True)}")
    except (TypeError, ValueError) as e:
        print(f"   （解析失败：{e}）")
else:
    print("⚠ **没有任何一行带块表** ⇒ 该算例的 `--pair-every` 可能没命中，")
    print("   或块表列在新版代码里才落盘。用 `nslab_n` 与 `Vt` 做替代读数：")
    print("\n" + " | ".join(f"{k:>10}" for k in have))
    for r in rows[::max(1, len(rows) // nshow)][:nshow]:
        print(" | ".join(f"{str(r.get(k,''))[:10]:>10}" for k in have))
