#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_recent_dbg.py —— 找近期写出的 `nuc_dbg.json`（按 mtime 排序，含父目录名）。"""
import os
import time

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp",
         "/mnt/f/_exp",
         "/mnt/f/speed_up/_exp"]
hits = []
for r in ROOTS:
    if not os.path.isdir(r):
        print(f"（跳过，不存在）{r}")
        continue
    for dp, dn, fn in os.walk(r):
        if "nuc_dbg.json" in fn:
            fp = os.path.join(dp, "nuc_dbg.json")
            try:
                hits.append((os.path.getmtime(fp), fp, os.path.getsize(fp)))
            except OSError:
                pass
# 也直接找名字里含 smok 的目录
extra = []
for r in ROOTS:
    if not os.path.isdir(r):
        continue
    for dp, dn, fn in os.walk(r):
        base = os.path.basename(dp)
        if "smok" in base.lower():
            extra.append(dp)
        if dp.count(os.sep) - r.count(os.sep) > 4:
            dn[:] = []
print(f"\n=== 全部 nuc_dbg.json（{len(hits)} 个，按 mtime 倒序前 8）===")
for mt, fp, sz in sorted(hits, reverse=True)[:8]:
    print(f"  {time.strftime('%m-%d %H:%M:%S', time.localtime(mt))}  {sz:>9}  {fp}")
print(f"\n=== 名字含 'smok' 的目录（{len(extra)} 个，前 12）===")
for e in sorted(set(extra))[:12]:
    print("  ", e)
