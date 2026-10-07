#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r251_projcheck.py —— ★ **判定影响面**：哪些归档臂带 `--facet-proj > 0`？

## 为什么必须查（否则 §144 的结论没有落点）

`_r249`/`_r250` 实测：**带 `--facet-proj 10` 时，γ_F3 改 31.3× ⇒ 形态量零变化**
（`f3_area`/`nf3`/`Vt`/`n_lath`/`w_lath`/`f3_pos` 的端点相对差全为 **0.000e+00**）；
**不带时** ⇒ 最大相对差 **0.91**。

**⇒ 若归档的"自协调"臂、R165、`_r225` 都带 `--facet-proj 10`，
  那本会话一整串"界面能量不到"就有了**同一个配置级根因**。**

⚠ `facet_proj` **不是 meta 顶层键**（`§129` 的教训：λ 也只在 `exp_args` 里）
⇒ 必须读 `exp_args.facet_proj`。
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


def fac(m):
    """读 `--facet-proj`：优先顶层，其次 `exp_args`（`§129.4` 的教训）。"""
    if 'facet_proj' in m:
        v = m['facet_proj']
        return v, '顶层'
    ea = m.get('exp_args') or {}
    if 'facet_proj' in ea:
        return ea['facet_proj'], 'exp_args'
    return None, '**两处都没有**'


def main():
    print('=' * 104)
    print('_r251 —— 哪些臂带 `--facet-proj > 0`？')
    print('=' * 104)
    arms = sorted(d for d in os.listdir(MB)
                  if d.startswith('dry_') and os.path.isdir(os.path.join(MB, d)))
    on, off, unk = [], [], []
    for a in arms:
        p = os.path.join(MB, a, 'meta.json')
        if not os.path.exists(p):
            continue
        try:
            m = json.load(open(p))
        except (OSError, ValueError):
            continue
        v, src = fac(m)
        try:
            vi = int(v) if v is not None else None
        except (TypeError, ValueError):
            vi = None
        (on if (vi or 0) > 0 else (off if vi == 0 else unk)).append((a, v, src))
    print('  归档臂总数（有 meta 的）= %d' % (len(on) + len(off) + len(unk)))
    print()
    print('  ## **带 `--facet-proj > 0`**（界面能效应可能被压制）= **%d 个**' % len(on))
    for (a, v, src) in on:
        print('     %-24s facet_proj=%-5s (读自 %s)' % (a, v, src))
    print()
    print('  ## **`--facet-proj = 0`（或不带）** = **%d 个**（前 25）' % len(off))
    for (a, v, src) in off[:25]:
        print('     %-24s facet_proj=%-5s (读自 %s)' % (a, v, src))
    print()
    if unk:
        print('  ## ⚠ **读不到 `facet_proj`** = %d 个（前 15）' % len(unk))
        for (a, v, src) in unk[:15]:
            print('     %-24s v=%-6s %s' % (a, v, src))
    print()
    print('=' * 104)
    print('  ## 本会话关键臂的落点')
    print('=' * 104)
    KEY = ('saSet2', 'saSet2F2', 'saOddG', 'saOddGF2', 'saSet2INERT', 'saSet2DT',
           'p45L', 'p45P', 'mb2fp10', 'mb2fp0', 'sgG', 'mo1fp10', 'mo1fp0',
           'swN128', 'swINV128', 't1N112L800')
    for k in KEY:
        p = os.path.join(MB, 'dry_' + k, 'meta.json')
        if not os.path.exists(p):
            printf = '     %-14s （不存在）' % k
            print(printf)
            continue
        m = json.load(open(p))
        v, src = fac(m)
        print('     %-14s facet_proj=%-6s (读自 %s)  %s'
              % (k, v, src, '← **>0 ⇒ 界面能可能被压制**' if (v or 0) else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
