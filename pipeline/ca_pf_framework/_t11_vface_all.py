#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vface_all.py <tag> —— 全场统计 `v_tip/v_wide`（长厚速度比），报分布而非单场。

⚠ 纪律（本轮教训）：**单场数值离散很大**（场 2 给 4.53、场 3 给 2.38）⇒
   **必须报分布（中位+范围+场数）**，且**与基线臂对照**（负对照必须有分辨力）。
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def load(step, tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        return (np.asarray(z['region']).astype(np.int32),
                np.asarray(z['a_ax'], float), np.asarray(z['w_ax'], float),
                np.asarray(z['n_hab'], float))


def offsets(tag, step, field):
    t = load(step, tag)
    if t is None:
        return None
    reg, a, w, nh = t
    m = (reg == field)
    if m.sum() < 60:
        return None
    d = distance_transform_edt(m)
    g = np.gradient(d, DX)
    gn = np.sqrt(sum(x ** 2 for x in g))
    band = m & (d <= 3.0) & (gn > 1e-9)
    if band.sum() < 60:
        return None
    nx = np.stack([g[0][band], g[1][band], g[2][band]], axis=1)
    nx = nx / np.maximum(np.linalg.norm(nx, axis=1, keepdims=True), 1e-300)
    pos = np.argwhere(band).astype(float) * DX
    c = np.argwhere(m).astype(float).mean(0) * DX
    out = {}
    for name, comp, ax in (('tip', nx @ a, a), ('side', nx @ w, w),
                           ('wide', nx @ nh, nh)):
        sel = comp ** 2 > 0.81
        if sel.sum() < 25:
            out[name] = np.nan
            continue
        off = (pos[sel] - c) @ ax
        out[name] = float(np.mean(off[off > 0])) * 1e9 if (off > 0).sum() > 12 \
            else float(np.mean(np.abs(off))) * 1e9
    return out


for tag in (sys.argv[1:] or ["kW1"]):
    t = tag[4:] if tag.startswith('dry_') else tag
    sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % t, "snap_*.npz")))
    steps = []
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            steps.append(int(np.asarray(z['step']).ravel()[0]))
    steps.sort()
    if len(steps) < 3:
        print("【%s】快照不足" % t)
        continue
    s0, s1 = steps[2], steps[-1]
    reg0 = load(s0, t)
    if reg0 is None:
        continue
    flds = sorted(int(v) for v in np.unique(reg0[0]) if v > 0)
    print("=" * 92)
    print("【%s】全场 `v_tip/v_wide`（step %d→%d，%d 个场）" % (t, s0, s1, len(flds)))
    print("=" * 92)
    print("  %-6s %-10s %-10s %-10s %-11s %-11s"
          % ('场', 'v_tip', 'v_side', 'v_wide', 'tip/wide', 'tip/side'))
    tw, ts = [], []
    for k in flds:
        o0, o1 = offsets(t, s0, k), offsets(t, s1, k)
        if o0 is None or o1 is None:
            continue
        ds = max(s1 - s0, 1)
        vt = (o1['tip'] - o0['tip']) / ds
        vs = (o1['side'] - o0['side']) / ds
        vw = (o1['wide'] - o0['wide']) / ds
        r1 = vt / vw if vw > 1e-9 else np.nan
        r2 = vt / vs if vs > 1e-9 else np.nan
        if np.isfinite(r1):
            tw.append(r1)
        if np.isfinite(r2):
            ts.append(r2)
        print("  %-6d %-10.3f %-10.3f %-10.3f %-11s %-11s"
              % (k, vt, vs, vw,
                 ('%.2f' % r1) if np.isfinite(r1) else 'nan',
                 ('%.2f' % r2) if np.isfinite(r2) else 'nan'))
    if tw:
        print("\n  ⇒ **`v_tip/v_wide` 中位 = %.2f**（%d 个场；范围 %.2f–%.2f）"
              % (float(np.median(tw)), len(tw), min(tw), max(tw)))
    if ts:
        print("  ⇒ **`v_tip/v_side` 中位 = %.2f**（%d 个场；范围 %.2f–%.2f）"
              % (float(np.median(ts)), len(ts), min(ts), max(ts)))
