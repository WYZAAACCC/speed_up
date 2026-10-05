#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_exp_args.py —— 打印算例 exp_args 全文 + vmap/laths 结构摘要（不 dump 巨型字典）。

用法: _t11_exp_args.py <tag> [<tag> ...]
"""
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(ROOT, "_exp", "_bk_t5")


def main() -> int:
    tags = sys.argv[1:] or ["dry_t10B9"]
    for tag in tags:
        p = os.path.join(EXP, tag, "meta.json")
        if not os.path.exists(p):
            print(f"!! {p} 不存在")
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        print(f"\n{'#'*100}\n### {tag}\n{'#'*100}")

        ea = d.get("exp_args", {})
        print(f"\n--- exp_args ({len(ea)} 键) ---")
        for k in sorted(ea):
            print(f"  {k:<26} {ea[k]}")

        # vmap 结构
        vm = d.get("vmap", {})
        if vm:
            grp2f = defaultdict(list)
            for f, g in vm.items():
                grp2f[g].append(int(f))
            print(f"\n--- vmap 结构：{len(vm)} 个场 → {len(grp2f)} 组 ---")
            for g in sorted(grp2f, key=lambda x: (isinstance(x, str), x)):
                fs = sorted(grp2f[g])
                print(f"  组 {g}: n={len(fs)}  场 {fs[0]}..{fs[-1]}")
            c = Counter(vm.values())
            print(f"  每组场数分布: {dict(c)}")
        la = d.get("laths", [])
        if la:
            print(f"\n--- laths 列表 n={len(la)} ---")
            print(f"  值分布: {dict(Counter(la))}")
            # 连续段
            segs, s = [], 0
            for i in range(1, len(la) + 1):
                if i == len(la) or la[i] != la[s]:
                    segs.append((la[s], s + 1, i))
                    s = i
            print(f"  连续段 {len(segs)} 个: {[(v, a, b) for v, a, b in segs]}")
        for key in ("gamma_RS", "theta_deg"):
            t = d.get(key, {})
            if t:
                vals = [v for v in t.values() if isinstance(v, (int, float))]
                import math
                nan = sum(1 for v in vals if isinstance(v, float) and math.isnan(v))
                fin = [v for v in vals if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))]
                print(f"\n--- {key}: n={len(t)}  非NaN={len(fin)}  NaN={nan}")
                if fin:
                    print(f"  min={min(fin):.6g} max={max(fin):.6g} "
                          f"mean={sum(fin)/len(fin):.6g} 唯一值数={len(set(fin))}")
                    print(f"  前 6 项: {list(t.items())[:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
