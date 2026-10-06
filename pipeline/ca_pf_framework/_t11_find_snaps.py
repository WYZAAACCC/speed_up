#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_find_snaps.py —— 找**含多个场**的归档快照（用于量"引擎造出的核"形状）。"""
import glob
import os

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
rows = []
for d in sorted(glob.glob(os.path.join(ROOT, "dry_*"))):
    sns = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    if not sns:
        continue
    best = None
    for sp in sns:
        try:
            with np.load(sp, allow_pickle=False) as z:
                reg = np.asarray(z['region'])
                nf = len([v for v in np.unique(reg) if v != 0])
                step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        except Exception:                       # noqa: BLE001
            continue
        if best is None or nf > best[1]:
            best = (sp, nf, step)
    rows.append((best[1], len(sns), best[2], os.path.basename(d),
                 os.path.basename(best[0]), os.path.getsize(best[0])))
rows.sort(reverse=True)
print("=== 归档快照：按「最多场数」排序（前 22）===")
print("  %-6s %-6s %-8s %-34s %-18s %s"
      % ('最大场数', '快照数', '末step', '算例', '快照文件', '字节'))
for nf, ns, step, tag, fn, sz in rows[:22]:
    print("  %-6d %-6d %-8d %-34s %-18s %d" % (nf, ns, step, tag, fn, sz))
print("\n  总计 %d 个含快照的算例" % len(rows))
