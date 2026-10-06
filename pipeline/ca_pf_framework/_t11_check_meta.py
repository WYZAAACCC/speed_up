#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_check_meta.py —— 排查「`--out` 为什么没被发出去」（我这一轮的错）。

用法: _t11_check_meta.py
"""
import _t11_argparse_meta as AM

m = AM.build_meta()
print(f"META 共 {len(m)} 项")
for k in ("out", "tag", "T-end", "pf-phi", "ckpt-dir", "resume"):
    print(f"  META[{k!r:12}] -> {m.get(k)!r}")

# 归一化表（与 `_t11_prod_cmd.py` 同一套逻辑）
NORM = {}


def _norm(x):
    return str(x).lstrip('-').replace('_', '-').lower()


for k in m:
    NORM.setdefault(_norm(k), k)
    for al in m[k].get('aliases', []):
        NORM.setdefault(_norm(al), k)

print("\n归一化查表：")
for key in ("out", "tag"):
    print(f"  {key!r} -> META 直查={key in m}  归一化={NORM.get(_norm(key))!r}")

# `exp_args` 里到底有没有 out/tag
import json
import os
p = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_t10B9/meta.json"
ea = (json.load(open(p, encoding="utf-8")).get("exp_args") or {})
print(f"\nexp_args 里有 out? {'out' in ea}   值={ea.get('out')!r}")
print(f"exp_args 里有 tag? {'tag' in ea}   值={ea.get('tag')!r}")
