#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_frag.py <tag> [...] —— 碎片的**尺寸分布**（查"碎成小渣"还是"撕裂成大块"）。

判据：对每个场，列出各连通分量的胞数（降序），并给出
  · 最大分量占比（1.0 ⇒ 未碎）
  · 分量数
  · "小渣"（< 50 胞）的数量与占比 —— 小渣提示**数值性断裂**，
    大块撕裂提示**物理性失稳**（两者处置完全不同）。
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _t11_shape2 import ncomp  # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tags = [t[4:] if t.startswith('dry_') else t for t in (sys.argv[1:] or ["c2Eq0"])]
for tag in tags:
    sns = sorted(glob.glob(os.path.join(ROOT, "dry_%s" % tag, "snap_*.npz")))
    print("=" * 104)
    print("【%s】碎片尺寸分布（%d 个快照）" % (tag, len(sns)))
    print("=" * 104)
    for sp in sns:
        with np.load(sp, allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        print("\n  ◆ step=%d" % st)
        print("    %-5s %-8s %-6s %-9s %-9s %-30s %s"
              % ('场', '总胞数', '分量', '最大分量', '占本场', '各分量胞数(前 8)', '小渣<50'))
        for k in sorted(int(v) for v in np.unique(reg) if v > 0):
            m = (reg == k)
            tot = int(m.sum())
            if tot < 8:
                continue
            nc, lab = ncomp(m)
            if lab is None:
                continue
            szs = np.bincount(lab.ravel())
            szs = sorted((int(x) for x in szs[1:] if x > 0), reverse=True)
            big = szs[0] if szs else 0
            small = [x for x in szs if x < 50]
            print("    %-5d %-8d %-6d %-9d %-9.1f%% %-30s %d 个(共 %d 胞)"
                  % (k, tot, len(szs), big, 100.0 * big / max(tot, 1),
                     str(szs[:8])[:30], len(small), sum(small)))
