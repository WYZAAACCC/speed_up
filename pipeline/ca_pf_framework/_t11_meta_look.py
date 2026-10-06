#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_meta_look.py <tag> [...] —— 读 meta.json 里的**构造期计时/阶段**证据。"""
import json
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
KEYS = ("build", "construct", "pair_normals", "t_build", "wall", "timing",
        "prof", "account", "phase", "n_threads", "nthreads", "steps",
        "snap_every", "beta_h", "plate_L", "plate_W", "plate_T", "tag")
for tag in (sys.argv[1:] or ["c2B647"]):
    p = os.path.join(ROOT, "dry_%s" % tag, "meta.json")
    print("=" * 90)
    if not os.path.exists(p):
        print("【%s】无 meta.json" % tag)
        continue
    j = json.load(open(p, encoding="utf-8"))
    print("【%s】顶层键：%s" % (tag, sorted(j.keys())[:30]))
    a = j.get("exp_args", {})
    for k in KEYS:
        for src, name in ((a, 'args'), (j, 'top')):
            if k in src:
                print("   [%s] %-16s = %r" % (name, k, src[k]))
    # 任何含"秒"/"s"的计时类键
    for src, name in ((a, 'args'), (j, 'top')):
        for k, v in src.items():
            if any(t in k.lower() for t in ("build", "wall", "sec", "time", "prof")):
                print("   [%s] %-24s = %r" % (name, k, v))
