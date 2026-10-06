#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_shape_cmp.py <tagA> <tagB> [...] —— **同 step 对照两/多臂的形状与长厚比**。

## 判据
`L1`（`facet_proj=1`）vs `L0`（0）：同 step 上比
  · 界面胞总数（`ncell`）
  · 该场**最大连通分量**的 `R1/R3`（长/厚，**只用主体**，避免孤儿胞污染二阶矩，`P22`）
⇒ 若 `L1` 的长厚比在**同 step** 上高于 `L0` ⇒ **投影真的促成了伸长**。
"""
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
from _t11_shape2 import ncomp, shape_metrics  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tags = sys.argv[1:] or ["L0", "L1"]


def snap(tag, step):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % step)
    if not os.path.exists(p):
        return None
    with np.load(p, allow_pickle=False) as z:
        return (np.asarray(z['region']).astype(np.int32),
                np.asarray(z['a_ax'], float), np.asarray(z['w_ax'], float),
                np.asarray(z['n_hab'], float))


def steps_of(tag):
    d = os.path.join(ROOT, "dry_%s" % tag)
    out = []
    for f in sorted(os.listdir(d)):
        if f.startswith("snap_"):
            with np.load(os.path.join(d, f), allow_pickle=False) as z:
                out.append(int(np.asarray(z['step']).ravel()[0]))
    return sorted(out)


S = {t: steps_of(t) for t in tags}
common = sorted(set.intersection(*[set(v) for v in S.values()]))
print("=" * 100)
print("同 step 形状对照：%s    共有 step %d 个（%s … %s）"
      % (' vs '.join(tags), len(common), common[0] if common else '—',
         common[-1] if common else '—'))
print("=" * 100)
hdr = "  %-6s" % 'step'
for t in tags:
    hdr += " %-26s" % ('%s: 主体胞 R1/R3' % t)
print(hdr)
for st in common:
    if st % 50:
        continue
    line = "  %-6d" % st
    for t in tags:
        s = snap(t, st)
        if s is None:
            line += " %-26s" % '—'
            continue
        reg, a, w, nh = s
        # 只取全场最大的连通分量（跨所有场），代表"主体"
        allm = (reg > 0)
        nc, lab = ncomp(allm)
        if lab is None:
            line += " %-26s" % '无场'
            continue
        szs = np.bincount(lab.ravel()); szs[0] = 0
        m = (lab == int(np.argmax(szs)))
        met = shape_metrics(np.argwhere(m).astype(np.float64) * DX, a, w, nh)
        nf = len(set(np.unique(reg).tolist()) - {0})
        line += " %-26s" % ('%.2f（%d胞,%d场）' % (met['elong_lt'], m.sum(), nf))
    print(line)
print()
print("  说明：`R1/R3` = 回转张量最大/最小主半轴（**基无关**，`R628 §9`）；")
print("        括号内 = 该主体胞数 + 该 step 的场数。")
