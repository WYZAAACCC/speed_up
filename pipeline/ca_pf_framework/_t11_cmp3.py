#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cmp3.py <tag>["@step"] ... —— **多臂在同一 step 上并排**报逐场长厚比。

用法：`_t11_cmp3.py L1 B10 B40`（各取自己最后一个未撞盒 step）
      `_t11_cmp3.py L1@300 B10@300 B40@300`（**锁定同一 step**，最可比）
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def touch_of(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = int(r.get('box_touch') or 0)
            except (KeyError, ValueError):
                pass
    return d


def steps_of(tag):
    d = os.path.join(ROOT, "dry_%s" % tag)
    out = []
    for f in sorted(os.listdir(d)):
        if f.startswith("snap_"):
            with np.load(os.path.join(d, f), allow_pickle=False) as z:
                out.append(int(np.asarray(z['step']).ravel()[0]))
    return sorted(out)


def perfield(tag, st):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        a, w, nh = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
    lams = []
    for k in sorted(int(v) for v in np.unique(reg) if v > 0):
        m = (reg == k)
        if m.sum() < 100:
            continue
        nc, lab = ncomp(m)
        if lab is not None and nc > 1:
            s = np.bincount(lab.ravel()); s[0] = 0
            m = (lab == int(np.argmax(s)))
        if m.sum() < 100:
            continue
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        lams.append(met['elong_lt'])
    return lams or None


specs = []
for a in (sys.argv[1:] or ["L1", "B10", "B40"]):
    t, _, s = a.partition('@')
    specs.append((t, int(s) if s else None))
print("=" * 96)
print("逐场长厚比并排（`Λ` = R1/R3，基无关；只统计 ≥100 胞的场）")
print("=" * 96)
print("  %-8s %-8s %-8s %-9s %-9s %-9s %s"
      % ('臂', 'step', '撞盒', '场数', 'Λ 中位', 'Λ 最大', '各场 Λ'))
for t, want in specs:
    tc = touch_of(t)
    sts = steps_of(t)
    if not sts:
        print("  %-8s （无快照）" % t)
        continue
    if want is None:
        ok = [s for s in sts if not tc.get(s, 0)]
        st = (ok or sts)[-1]
    else:
        st = want if want in sts else min(sts, key=lambda s: abs(s - want))
    lam = perfield(t, st)
    if not lam:
        print("  %-8s %-8d %-8s （无足够大的场）" % (t, st, tc.get(st, '?')))
        continue
    print("  %-8s %-8d %-8s %-9d %-9.2f %-9.2f %s"
          % (t, st, tc.get(st, '?'), len(lam), float(np.median(lam)), max(lam),
             ' '.join('%.1f' % x for x in sorted(lam, reverse=True)[:8])))
