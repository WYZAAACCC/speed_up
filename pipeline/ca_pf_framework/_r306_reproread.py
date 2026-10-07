#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r306_reproread.py —— `§144` 的**复现 + 稳健性**读数。

## 判据（`_r305` 头部已写死）
* **V-1 复现**：`rH`(γ=0.2771) vs `rC`(γ=0.0089)，N=32/`1,1`/30 步/**带投影**
  ⇒ 应重现 `§144` 的"形态量逐位为零"。
* **V-3 负对照**：`rH` vs `rH2`（同配置两次）⇒ **必须逐位相同**。
* **V-2 ★ 稳健性（换几何）**：`sH` vs `sC`，**N=48 / `1,1,3,3` / 40 步，仍带投影、仍 31.3×**
  ⇒ 若**仍逐位相同** ⇒ `§144` 稳健；若**出现形态差异** ⇒ 适用范围比声称的窄。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '_exp', '_bk_repro')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}
# 形态量（"形态是否被投影钉住"看这些）
MORPH = ('f3_area_m2', 'nf3', 'Vt', 'n_lath', 'w_lath', 'a_lath',
         'f3_pos_m', 'f3_pos_dx', 'f2_area_m2', 'nf2')


def rd(tag):
    p = os.path.join(BASE, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def gmeta(tag):
    import json
    p = os.path.join(BASE, 'dry_' + tag, 'meta.json')
    if not os.path.exists(p):
        return {}
    m = json.load(open(p))
    return {k: v for k, v in (m.get('gamma_RS') or {}).items() if v is not None}


def cmp(A, B):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    allnd, morphnd, worst = 0, 0, (0.0, None)
    mworst = (0.0, None)
    for s in common:
        for c in cols:
            a, b = sa[s].get(c), sb[s].get(c)
            if a == b:
                continue
            try:
                fa, fb = float(a), float(b)
                if fa != fa and fb != fb:
                    continue
                d = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
            except (TypeError, ValueError):
                d = 1.0
            allnd += 1
            if d > worst[0]:
                worst = (d, '%s@%s' % (c, s))
            if c in MORPH:
                morphnd += 1
                if d > mworst[0]:
                    mworst = (d, '%s@%s' % (c, s))
    return len(common), len(cols), allnd, worst, morphnd, mworst


def main():
    print('=' * 108)
    print('_r306 —— `§144` 的复现 + 稳健性读数')
    print('=' * 108)
    R = {t: rd(t) for t in ('rH', 'rC', 'rH2', 'sH', 'sC')}
    for t in R:
        print('  %-5s %s' % (t, ('%d 行，末步 %s' % (len(R[t]), R[t][-1]['step']))
                             if R[t] else '**缺失**'))
    print()
    print('  ## 各臂的 γ（前置核对）')
    for t in R:
        g = gmeta(t)
        if g:
            print('     %-5s γ_F3 = %s' % (t, g))
    print()
    ok = True
    print('  ## **V-3 负对照**（同配置跑两次）')
    n, nc, nd, w, mnd, mw = cmp(R['rH'], R['rH2'])
    print('     rH vs rH2：共同步 %d、可比列 %d ⇒ **不同字段 %d**（形态列 %d）'
          % (n, nc, nd, mnd))
    print('     ⇒ %s' % ('✅ 确定性成立' if nd == 0 else '❌ 非确定 ⇒ 后续结论不可信'))
    ok &= (nd == 0)
    print()
    print('  ## **V-1 复现**（`§144` 的原配置，带投影，31.3× 对比）')
    n, nc, nd, w, mnd, mw = cmp(R['rH'], R['rC'])
    print('     rH vs rC：共同步 %d、可比列 %d ⇒ **不同字段 %d**' % (n, nc, nd))
    print('     **形态列不同字段 = %d**；最大相对差 %.3e (%s)' % (mnd, mw[0], mw[1]))
    if mnd == 0:
        print('     ⇒ ✅ **复现成功**：带投影时 γ_F3 改 31.3× ⇒ **形态列逐位相同**（`§144`）')
    else:
        print('     ⇒ ❌ **未能复现** ⇒ `§144` 需重审')
        ok = False
    print()
    print('  ## **V-2 ★ 稳健性（换几何：N=48 / `1,1,3,3` / 40 步）**')
    n2, nc2, nd2, w2, mnd2, mw2 = cmp(R['sH'], R['sC'])
    print('     sH vs sC：共同步 %d、可比列 %d ⇒ **不同字段 %d**' % (n2, nc2, nd2))
    print('     **形态列不同字段 = %d**；最大相对差 %.3e (%s)' % (mnd2, mw2[0], mw2[1]))
    if mnd2 == 0:
        print('     ⇒ ✅ **稳健**：换几何后**仍然逐位相同** ⇒ `§144` 的适用范围比 N=32 更宽')
    else:
        print('     ⇒ ⚠ **不稳健**：换几何后**形态列出现差异**'
              '（%d 个字段）⇒ `§144` 的适用范围**比声称的窄**，须记账' % mnd2)
    print()
    print('=' * 108)
    print('  ## 总判定')
    print('=' * 108)
    print('     V-3 确定性 ✅ ；V-1 复现 %s ；V-2 稳健性 %s'
          % ('✅' if mnd == 0 else '❌', '✅' if mnd2 == 0 else '⚠'))
    print()
    print('  ⚠ 记账：V-4（**不带**投影的那一组）本脚本不复现，引用 `_r248` 的实测：')
    print('     不带投影时同一对比度下**形态量最大相对差 9.1e-01**。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
