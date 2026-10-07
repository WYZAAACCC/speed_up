#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r249_projread.py —— H-1 检验的读数：`--facet-proj` 是否压制界面能效应。

对比两组（**几何逐字相同，只差 `--facet-proj`**）：
* **无投影**（`_r246`/`_r247`）：`qH`(γ=0.2771) vs `qC`(γ=0.0089)，对比 **31.3×**
* **有投影**（`_r248`）：`qHp` vs `qCp`，同样的 γ 对比，加 `--facet-proj 10`

判据：
* **P-1** 负对照（同配置跑两次）必须逐步逐位相同。
* **P-2** ★ 两组的分叉步数占比对比。
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s', 'dt'}


def rows(root, tag):
    p = os.path.join(HERE, root, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with io.open(p, 'r', encoding='utf-8') as f:
        r = list(csv.DictReader(f))
    mf = os.path.join(HERE, root, 'dry_' + tag, 'meta.json')
    m = json.load(open(mf)) if os.path.exists(mf) else {}
    return r, m


def stats(A, B):
    sa = {x['step']: x for x in A}
    sb = {x['step']: x for x in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    same, diff = 0, []
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
        if nd:
            diff.append((s, nd, worst))
        else:
            same += 1
    return len(common), len(cols), same, diff


def main():
    print('=' * 108)
    print('_r249 —— H-1 检验：`--facet-proj` 是否压制界面能效应？')
    print('=' * 108)
    groups = [('**无投影**', '_exp/_bk_q17', 'qH', 'qC', 'qH2'),
              ('**有投影** `--facet-proj 10`', '_exp/_bk_q18', 'qHp', 'qCp', 'qH2p')]
    res = {}
    for label, root, tA, tB, tN in groups:
        A, mA = rows(root, tA)
        B, mB = rows(root, tB)
        N, mN = rows(root, tN)
        if A is None or B is None or N is None:
            print('\n  ## %s：⚠ 缺数据' % label)
            continue
        gA = [v for v in (mA.get('gamma_RS') or {}).values() if v is not None]
        gB = [v for v in (mB.get('gamma_RS') or {}).values() if v is not None]
        print()
        print('  ' + '=' * 104)
        print('  ## %s' % label)
        print('     `--facet-proj` = %s' % mA.get('facet_proj'))
        print('     γ_F3：%s = **%.6f** ；%s = **%.6f** ⇒ 对比 **%.1f×**'
              % (tA, max(gA), tB, min(gB), max(gA) / min(gB) if min(gB) > 0 else float('nan')))
        # 负对照
        n1, nc1, s1, d1 = stats(A, N)
        print('     **P-1 负对照** %s vs %s：相同步 %d / %d ⇒ %s'
              % (tA, tN, s1, n1, '✅ 确定' if not d1 else '❌ 非确定'))
        # 处理对比
        n2, nc2, s2, d2 = stats(A, B)
        frac = len(d2) / max(n2, 1)
        print('     **P-2 处理对比** %s vs %s：**分叉 %d / %d 步（%.0f%%）**'
              % (tA, tB, len(d2), n2, 100 * frac))
        if d2:
            ws = [w for (_, _, w) in d2]
            print('        最大相对差：首 %.3e → 末 %.3e' % (ws[0], ws[-1]))
        res[label] = dict(frac=frac, n=n2, nd=len(d2), det=(not d1))
    print()
    print('=' * 108)
    print('  ## 判定')
    print('=' * 108)
    ks = list(res)
    if len(ks) == 2:
        f0, f1 = res[ks[0]]['frac'], res[ks[1]]['frac']
        print('     无投影：分叉 **%.0f%%**；有投影：分叉 **%.0f%%**' % (100 * f0, 100 * f1))
        if f1 < 0.5 * f0:
            print('     ⇒ ✅ **H-1 得到支持**：`--facet-proj` **显著压低**了 γ_F3 的影响')
            print('        ⇒ 这是一条**统一解释**：归档的自协调臂几乎全带 `--facet-proj 10`')
            print('          ⇒ `§99`/`§132.5`/`§135.2`/Q-17 的"量不到"**可能有同一个根因**。')
        elif f1 > 0.8 * f0:
            print('     ⇒ ❌ **H-1 被否**：投影没有压低 γ_F3 的影响')
            print('        ⇒ `_r225` 的"只有 step 80 分叉"必须另找解释。')
        else:
            print('     ⇒ ⚠ 部分压低（%.0f%% → %.0f%%），不足以定论。' % (100 * f0, 100 * f1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
