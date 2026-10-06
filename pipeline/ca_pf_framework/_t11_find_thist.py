#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_thist.py <tag...> —— 找 `T_hist`（逐事件记录）落在哪个文件/键里。"""
import json
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
tags = sys.argv[1:] or ["dry_t10PROD1"]
for tag in tags:
    d = next((os.path.join(b, tag) for b in BASES
              if os.path.isdir(os.path.join(b, tag))), None)
    print("=" * 90)
    print("【%s】 %s" % (tag, d))
    if d is None:
        print("  **不存在**")
        continue
    for fn in sorted(os.listdir(d)):
        fp = os.path.join(d, fn)
        if not os.path.isfile(fp):
            print("  [dir] %s" % fn)
            continue
        sz = os.path.getsize(fp)
        print("  [file] %-20s %10d B" % (fn, sz))
        if fn.endswith(".json") and sz < 80_000_000:
            try:
                j = json.load(open(fp, encoding="utf-8"))
            except Exception as e:            # noqa: BLE001
                print("         （json 解析失败：%s）" % e)
                continue
            if isinstance(j, dict):
                ks = list(j.keys())
                print("         顶层键 %d 个：%s" % (len(ks), ks[:24]))
                for k in ks:
                    v = j[k]
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        print("         ★ `%s` 是 dict 列表（%d 条）⇒ **逐事件记录**"
                              % (k, len(v)))
                        print("           第 1 条键：%s" % list(v[0].keys()))
                        print("           末条：%s" % json.dumps(
                            v[-1], ensure_ascii=False)[:400])
