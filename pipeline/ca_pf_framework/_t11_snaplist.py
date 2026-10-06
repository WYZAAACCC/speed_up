#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_snaplist.py —— 列出三个臂**盘上实际的快照文件** + 各自的最新 step（权威口径）。"""
import glob
import os
import time

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
OUT = "/mnt/f/speed_up/_w2_snaplist.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
for t in ("c2Eq0", "c2B647", "c2PosA"):
    d = os.path.join(ROOT, "dry_%s" % t)
    L.append("【%s】%s" % (t, d))
    if not os.path.isdir(d):
        L.append("   （目录不存在）")
        continue
    fs = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    if not fs:
        L.append("   （无快照）")
    for f in fs:
        L.append("   %-20s %9d B  %s"
                 % (os.path.basename(f), os.path.getsize(f),
                    time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))))
    # 其它产物（ckpt / series）
    for pat in ("ckpt/*.npz", "series.csv", "meta.json", "seeds.npz"):
        for f in sorted(glob.glob(os.path.join(d, pat))):
            L.append("   %-20s %9d B  %s"
                     % (os.path.relpath(f, d), os.path.getsize(f),
                        time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(f)))))
    L.append("")
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
