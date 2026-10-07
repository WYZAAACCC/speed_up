#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_qdiag.py <tag>[@step] —— 诊断 Q 臂：为什么"无足够大的场"。

查：场号分布、每场胞数、`region` 取值、以及 `band_fld` 是否为空。
"""
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for spec in (sys.argv[1:] or ["Q0", "Q1", "L0"]):
    tag, _, st = spec.partition('@')
    d = os.path.join(ROOT, "dry_%s" % tag)
    if not os.path.isdir(d):
        print("【%s】无目录" % tag)
        continue
    if st:
        steps = [int(st)]
    else:
        steps = sorted(int(f[5:10]) for f in os.listdir(d) if f.startswith("snap_"))
        steps = steps[::max(1, len(steps) // 5)][:6]
    print("=" * 88)
    print("【%s】快照 step = %s" % (tag, steps))
    print("=" * 88)
    for s in steps:
        p = os.path.join(d, "snap_%05d.npz" % s)
        if not os.path.exists(p):
            continue
        with np.load(p, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            fld = np.asarray(z['band_fld'])
            # region 取值
            u, c = np.unique(reg, return_counts=True)
            occ = {int(a): int(b) for a, b in zip(u, c) if a > 0}
            fu = sorted(int(v) for v in np.unique(fld))
            print("  step %-5d region>0 的场: %-28s  带内 band_fld: %s"
                  % (s, str(occ)[:80], fu))
