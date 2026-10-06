#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_artifact_audit.py —— 审计产物目录里**哪些文件属于哪一次运行**（防混用）。

判据：`meta.json` 的 `steps` / `snap_every` / `tag` 是**该次运行自己的**权威；
      与快照的 `step` 字段、mtime 交叉核对 ⇒ 识别**跨运行的残留文件**。
"""
import glob
import json
import os
import time

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
OUT = "/mnt/f/speed_up/_w2_artifact_audit.txt"
L = ["#### %s" % time.strftime('%F %T'), ""]
for t in ("c2Eq0", "c2B647", "c2PosA"):
    d = os.path.join(ROOT, "dry_%s" % t)
    L.append("=" * 100)
    L.append("【%s】" % t)
    mj = os.path.join(d, "meta.json")
    msteps = msnap = None
    if os.path.exists(mj):
        j = json.load(open(mj, encoding="utf-8"))
        a = j.get("exp_args", j)
        msteps = a.get("steps")
        msnap = a.get("snap_every", a.get("snap-every"))
        L.append("  meta.json（%s，mtime=%s）：steps=%s  snap_every=%s  N=%s  tag=%s"
                 % (os.path.basename(mj),
                    time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(mj))),
                    msteps, msnap, a.get("N"), a.get("tag")))
    L.append("  %-20s %-10s %-9s %-11s %s"
             % ('文件', '内部step', '字节', 'mtime', '判定'))
    files = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    mtime_meta = os.path.getmtime(mj) if os.path.exists(mj) else 0
    for f in files:
        try:
            with np.load(f, allow_pickle=False) as z:
                st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -9
        except Exception as e:                          # noqa: BLE001
            st = 'ERR:%s' % e
        mt = os.path.getmtime(f)
        # 判据：该文件的 mtime 若**早于 meta.json** ⇒ 不可能属于本次运行
        stale = mt < mtime_meta - 1.0
        L.append("  %-20s %-10s %-9d %-11s %s"
                 % (os.path.basename(f), st, os.path.getsize(f),
                    time.strftime('%H:%M:%S', time.localtime(mt)),
                    '⚠⚠ **属于更早的运行（残留）**' if stale else '✅ 属于本次运行'))
    # 文件名 step 与内部 step 是否一致
    for f in files:
        nm = os.path.basename(f)
        try:
            nstep = int(nm.split('_')[1].split('.')[0])
        except (IndexError, ValueError):
            continue
        try:
            with np.load(f, allow_pickle=False) as z:
                ist = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -9
        except Exception:                               # noqa: BLE001
            continue
        if nstep != ist:
            L.append("  ⚠ 文件名 step=%d 与内部 step=%d **不一致**（%s）" % (nstep, ist, nm))
    L.append("")
open(OUT, 'w').write("\n".join(L) + "\n")
print("\n".join(L))
