#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_effcfg.py —— 硬步骤 A 的工具：打印算例**生效配置**，只取标量/小对象。

用法: _t11_effcfg.py <tag> [<tag> ...]
说明: meta.json 里 `vmap`(nv 项) 与 `pairs`(C(nv,2) 项) 是巨型字典，
      整份 dump 会爆输出（本轮已踩）。本工具只打标量键 + 巨型字典的"摘要统计"。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(ROOT, "_exp", "_bk_t5")
BIG = 40          # 超过这个长度/元素数就只打摘要


def summarize(v):
    if isinstance(v, dict):
        ks = list(v.keys())
        return f"<dict n={len(v)} keys[:3]={ks[:3]} ... keys[-2:]={ks[-2:]}>"
    if isinstance(v, (list, tuple)):
        return f"<list n={len(v)} head={list(v)[:3]}>"
    return v


def dump_one(tag):
    for name in ("meta.json", "closure.json"):
        p = os.path.join(EXP, tag, name)
        if not os.path.exists(p):
            print(f"  ({name} 不存在)")
            continue
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        print(f"\n=== {tag}/{name}  ({len(d)} 键) ===")
        for k in sorted(d):
            v = d[k]
            s = summarize(v)
            if isinstance(v, (dict, list, tuple)) or (isinstance(s, str) and len(s) > BIG):
                print(f"  {k:<26} {s}")
            else:
                print(f"  {k:<26} {v}")


def main() -> int:
    tags = sys.argv[1:]
    if not tags:
        tags = sorted(d for d in os.listdir(EXP) if os.path.isdir(os.path.join(EXP, d)))
        print(f"未给 tag ⇒ 列出 {len(tags)} 个算例目录")
        for t in tags:
            print(" ", t)
        return 0
    for t in tags:
        dump_one(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
