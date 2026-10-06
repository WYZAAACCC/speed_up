#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_cmp_arms.py <tagA> <tagB> —— **同 step 对齐**比较两臂的 `Vt` 与长厚比。

## 为什么要这个
本轮已撤回 4 次读数，**任何正向结果必须先核可复现性**。
本工具在**相同 step** 上比（避免 `P8` 的阶段错配），并报**逐位是否相同**：
  · `L2` vs `L1`（同配置）⇒ **应逐位相同**（`--block-seed` 固定 20261001）
  · `L1` vs `L0`（差 `facet_proj`）⇒ 应**不同**（否则该开关没生效）
"""
import csv
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9


def vt(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    d = {}
    if os.path.exists(p):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            try:
                d[int(r['step'])] = float(r['Vt'])
            except (KeyError, ValueError):
                pass
    return d


def snap(tag, step):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        return (np.asarray(z['region']).astype(np.int32),
                np.asarray(z['a_ax'], float), np.asarray(z['w_ax'], float),
                np.asarray(z['n_hab'], float))


A, B = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("L1", "L2")
va, vb = vt(A), vt(B)
common = sorted(set(va) & set(vb))
print("=" * 92)
print("A=%s  vs  B=%s   共有 step = %d 个（%s … %s）"
      % (A, B, len(common), common[0] if common else '—', common[-1] if common else '—'))
print("=" * 92)
print("  %-7s %-16s %-16s %-10s %s" % ('step', 'A.Vt', 'B.Vt', '相对差', '逐位'))
same = 0
for st in common:
    ra, rb = va[st], vb[st]
    d = abs(rb - ra) / max(abs(ra), 1e-300)
    bit = '✅ 相同' if ra == rb else '不同'
    if ra == rb:
        same += 1
    print("  %-7d %-16.6g %-16.6g %-10.2e %s" % (st, ra, rb, d, bit))
print()
print("  ⇒ `Vt` **逐位相同**的 step：%d / %d" % (same, len(common)))
# 快照 region 是否逐位相同（最强的可复现性判据）
for st in common[-3:]:
    sa, sb = snap(A, st), snap(B, st)
    if sa is None or sb is None:
        continue
    eq = bool(np.array_equal(sa[0], sb[0]))
    print("  ⇒ step %d 的 `region` 逐位：%s（A 场数=%d, B 场数=%d）"
          % (st, '✅ 相同' if eq else '❌ 不同',
             len(set(np.unique(sa[0]).tolist()) - {0}),
             len(set(np.unique(sb[0]).tolist()) - {0})))
