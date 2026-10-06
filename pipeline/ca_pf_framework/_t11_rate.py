#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_rate.py <tag...> —— 从 series.csv 的 (step, wall_s) 反推算例速率与预计总时长。

⚠ 读数纪律：`csv` 按列名读；`wall_s` 是**累计墙钟秒**（不是每步增量）。
"""
import csv
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
tags = sys.argv[1:] or ["dry_t10B9", "dry_t10PROD2", "dry_t10PROD1"]
for tag in tags:
    p = next((os.path.join(b, tag, "series.csv") for b in BASES
              if os.path.exists(os.path.join(b, tag, "series.csv"))), None)
    print("=" * 84)
    print("【%s】" % tag)
    if p is None:
        print("  **无 series.csv**")
        continue
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    if not rows:
        print("  0 行（表头未写或尚无数据）")
        continue
    print("  %d 行" % len(rows))

    def f(r, k):
        try:
            return float(r.get(k))
        except (TypeError, ValueError):
            return None
    st = [(f(r, 'step'), f(r, 'wall_s'), f(r, 'nslab_nu'), f(r, 'blk_laths'))
          for r in rows]
    st = [x for x in st if x[0] is not None and x[1] is not None]
    if not st:
        print("  step/wall_s 不可解析")
        continue
    print("  %-8s %-12s %-10s %-10s %s" % ('step', 'wall_s', 'Δwall', 'nslab_nu',
                                           'blk_laths'))
    prev = None
    for s, w, nu, bl in st[:6] + ([('...', '', '', '')] if len(st) > 12 else []) \
            + st[-6:]:
        if s == '...':
            print("     ...")
            continue
        d = '' if prev is None else '%.0f' % (w - prev)
        prev = w
        print("  %-8.0f %-12.1f %-10s %-10s %s" % (s, w, d, nu, bl))
    if len(st) >= 2:
        s0, w0 = st[0]
        s1, w1 = st[-1]
        if s1 > s0:
            per = (w1 - w0) / (s1 - s0)
            print("  ⇒ 平均 %.1f s / step（step %d→%d, wall %.0f→%.0f s）"
                  % (per, s0, s1, w0, w1))
            print("  ⇒ 本跑到 step %d 累计 %.0f s = %.1f h"
                  % (s1, w1, w1 / 3600.0))
            if s1 < 2200:
                print("  ⇒ 若线性外推到 step 2200 ⇒ 还需 %.1f h"
                      % ((2200 - s1) * per / 3600.0))
