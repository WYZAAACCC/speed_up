#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dbg_glob.py —— 诊断 `_t11_lath_traj.py` 里"快照 0 个"的原因。"""
import glob
import os

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
for tag in ("c2Eq0", "dry_t5AB_A", "dry_t5AB_B"):
    d = os.path.join(ROOT, "dry_%s" % tag)
    pat = os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz")
    print("tag=%-14s dir存在=%-5s glob=%3d  listdir=%3d"
          % (tag, os.path.isdir(d), len(glob.glob(pat)),
             len([f for f in os.listdir(d) if f.startswith('snap_')])
             if os.path.isdir(d) else -1))
    print("   pattern = %r" % pat)
