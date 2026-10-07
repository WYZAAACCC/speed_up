#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r84_steptime.py —— **从日志里把实测的「秒/步」抽出来**，与标度律预测并排。

## 为什么

`R30_AUDIT_LEDGER.md §86` 断言：「实测 **~19 s/步**（160 步用了约 50 min）；
而 §7.2c 的标度律对 `N=96 / nreg=7` 给 ≈3.5 s/步 ⇒ **慢了约 5 倍**」，
并把根因归到 `facet_project()` 每次重建坐标网格。

**但 R75 自己的日志写着 `2.2 s/步`（`--facet-proj 10`、N=96、nreg=7）**
⇒ 比标度律预测的 3.5 s/步**还快**。两个数不可能同时对。

⇒ 本脚本把**所有**相关日志里的逐步耗时抽出来，**用实测数字说话**：
   * 每行形如 `  [ 600] ... | 1.80s/步`
   * 标度律：秒/步 ≈ 0.507 × (N³·nreg/1e6)（§7.2c）
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'\[\s*(\d+)\]\s.*?\|\s*([\d.]+)s/步')
NREG = re.compile(r'nreg=(\d+)')
NX = re.compile(r'N=(\d+)')
DX = re.compile(r'Δx=([\d.]+)\s*nm')


def law(N, nreg):
    return 0.507 * (N ** 3) * nreg / 1e6


def main():
    pats = sys.argv[1:] or ['_w2_r7*.log', '_w2_r6*.log', '_w2_r5*.log']
    print('=' * 108)
    print('实测「秒/步」 vs 标度律 0.507×(N³·nreg/1e6)')
    print('=' * 108)
    print('  %-26s %-5s %-6s %-6s %-10s %-10s %-8s %s'
          % ('日志', 'N', 'nreg', '步数', '实测中位', '标度律', '比值', '备注'))
    rows = []
    for pat in pats:
        for p in sorted(glob.glob(os.path.join(HERE, pat))):
            txt = open(p, encoding='utf-8', errors='replace').read()
            ts = [float(m.group(2)) for m in PAT.finditer(txt)]
            if not ts:
                continue
            mN = NX.search(txt)
            mR = NREG.search(txt)
            N = int(mN.group(1)) if mN else 0
            nr = int(mR.group(1)) if mR else 0
            med = float(np.median(ts))
            L = law(N, nr) if (N and nr) else float('nan')
            note = ''
            if 'facet-proj' in txt or 'facet_proj' in txt:
                mm = re.search(r'facet.proj[= ]+(\d+)', txt)
                note = 'facet-proj=%s' % (mm.group(1) if mm else '?')
            rows.append((os.path.basename(p), N, nr, len(ts), med, L,
                         med / L if L == L and L > 0 else float('nan'), note))
    rows.sort(key=lambda r: -r[4])
    for r in rows:
        print('  %-26s %-5d %-6d %-6d %-10.2f %-10.2f %-8.2f %s'
              % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))
    print()
    print('  ⇒ 若**大部分**行的比值 ≈ 1，则「投影拖慢 5 倍」这条断言**站不住**，')
    print('     应当按实测撤回/改写（本仓库纪律：写进文档的数要能溯源）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
