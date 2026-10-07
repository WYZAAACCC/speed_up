#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r247_q17read.py —— Q-17 小实验的读数（含**负对照**）。

## 判据（`_r246` 头部已写死）

* **Q-1** `qH` 与 `qC` 的 `gamma_RS` 差 ~29×（前置检查）。
* **Q-5** ★ **负对照** `qH` vs `qH2`（**同配置跑两次**）：必须**逐步逐位相同**。
  **若不同 ⇒ 仿真本身非确定 ⇒ 整个对照实验无效**，必须先解决。
* **Q-2** `qH` vs `qC`：数出"物理列逐位相同的步数"与"不同的步数"。
* **Q-3/Q-4** 差异是**连续**（每步都不同、单调增长）还是**零星**？
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_q17')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s', 'dt'}


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def meta(tag):
    p = os.path.join(MB, 'dry_' + tag, 'meta.json')
    return json.load(open(p)) if os.path.exists(p) else None


def cmp_steps(A, B, label):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    same_steps, diff_steps = [], []
    for s in common:
        nd = 0
        worst = 0.0
        for c in cols:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                if (sa[s].get(c) or '') != (sb[s].get(c) or ''):
                    nd += 1
                continue
            if fa != fa and fb != fb:
                continue
            if repr(fa) != repr(fb):
                nd += 1
                worst = max(worst, abs(fa - fb) / max(abs(fa), abs(fb), 1e-300))
        (diff_steps if nd else same_steps).append((s, nd, worst))
    print('  ## %s：共同步 %d 个、可比列 %d 个' % (label, len(common), len(cols)))
    print('     **逐位相同的步数 = %d ；有差异的步数 = %d**'
          % (len(same_steps), len(diff_steps)))
    if diff_steps:
        print('     %-6s %-10s %s' % ('step', '不同列数', '最大相对差'))
        for (s, nd, w) in diff_steps[:40]:
            print('     %-6s %-10d %.4e' % (s, nd, w))
        ws = [w for (_, _, w) in diff_steps]
        print('     ⇒ 差异**是否单调增长**：首/中/末 = %.3e / %.3e / %.3e'
              % (ws[0], ws[len(ws) // 2], ws[-1]))
    return len(same_steps), len(diff_steps)


def main():
    print('=' * 104)
    print('_r247 —— Q-17 小实验读数（γ_F3 极端对比 29×，逐步）')
    print('=' * 104)
    H, C, H2 = rows('qH'), rows('qC'), rows('qH2')
    if H is None or C is None or H2 is None:
        print('  ⚠ 缺数据')
        return 2

    print()
    print('  ## **Q-1** 前置：两臂的 `gamma_RS`')
    for nm, m in (('qH', meta('qH')), ('qC', meta('qC'))):
        g = {k: v for k, v in (m.get('gamma_RS') or {}).items() if v is not None}
        print('     %-4s omega_mode=%-9s omega_max_deg=%-8s gamma_RS=%s'
              % (nm, m.get('omega_mode'), m.get('omega_max_deg'), g))
    gH = [v for v in (meta('qH').get('gamma_RS') or {}).values() if v is not None]
    gC = [v for v in (meta('qC').get('gamma_RS') or {}).values() if v is not None]
    if gH and gC and min(gC) > 0:
        print('     ⇒ 对比度 = **%.1f×**（%.6f / %.6f）'
              % (max(gH) / min(gC), max(gH), min(gC)))

    print()
    print('  ## **Q-5** ★ **负对照**：`qH` vs `qH2`（**同配置跑两次**）')
    ns, nd = cmp_steps(H, H2, 'qH vs qH2')
    if nd == 0:
        print('     ⇒ ✅ **逐步逐位相同 ⇒ 仿真确定性成立 ⇒ 对照实验有效**')
    else:
        print('     ⇒ ❌ **出现了差异 ⇒ 仿真非确定**（并行/浮点归约次序？）')
        print('        ⇒ **在查清之前，H vs C 的"差异"不可信**（硬规则：先证基准）')

    print()
    print('  ## **Q-2/Q-3/Q-4**：`qH`(γ=0.2771) vs `qC`(γ≈0.0095)')
    ns2, nd2 = cmp_steps(H, C, 'qH vs qC')

    print()
    print('=' * 104)
    print('  ## 判定')
    print('=' * 104)
    if nd == 0 and nd2 == 0:
        print('     ⇒ ❌❌ **γ_F3 改 29 倍，30 步内**零影响** ⇒ 比 `§143.5` 的 1.815× 更强：')
        print('        **F3 的 γ 在这个配置里根本进不了动力学。**')
        print('        ⇒ **`§138.3` 的推论（F3 纯界面能驱动）被推翻**，')
        print('           且这是一个**比 Q-17 更严重的接线问题**（记为 **Q-18**）。')
    elif nd == 0 and nd2 > 0:
        frac = nd2 / max(ns2 + nd2, 1)
        print('     ⇒ `qH` vs `qC`：**%d/%d 步不同（%.0f%%）**'
              % (nd2, ns2 + nd2, 100 * frac))
        if frac > 0.8:
            print('        ⇒ **几乎每步都分叉 ⇒ 界面没被"钉住" ⇒ `§143.5` 的假设被否**')
            print('           ⇒ `_r225` 的"8/9 步逐位相同"需另找解释。')
        else:
            print('        ⇒ **零星分叉 ⇒ 支持"界面被钉在网格上"的假设。**')
    else:
        print('     ⇒ ⚠ 负对照不过 ⇒ 本实验**不作结论**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
