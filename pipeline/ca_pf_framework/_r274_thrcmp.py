#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r274_thrcmp.py —— 用 `_r272` 的**部分产物**做并行不变性比较（step 0 与 20）。

## 背景（**先记账**）
`_r272` 我起了 5 个并发臂（1/2/4/8 线程 + 同线程负对照），
在**已有 6 个重进程**之上 ⇒ 被我的 10 min 工具超时**打断**，
只跑到 step 20（`th8` 只到 step 0）。
**⇒ 这是我的调度错误**（硬规则 ㉔ 的同类：起并发前没做时间预算）。

## 但**已有数据仍可用**
`th1`/`th2`/`th4`/`th2b` 都写到了 step 20 ⇒ **可以在 step 0 与 20 上比**。
判据（**先写死**）：
* **T-1** `th1` vs `th2` vs `th4`：物理列逐位相同。
* **T-2** `th2` vs `th2b`（**同线程数跑两次**）：逐位相同 ⇒ 负对照。
* **T-3** `th8` 只到 step 0 ⇒ **只在 step 0 上比**（并说明）。
"""
from __future__ import annotations

import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '_exp', '_bk_thr')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}


def rd(tag):
    p = os.path.join(BASE, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def cmp(A, B, label, only_steps=None):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    if only_steps is not None:
        common = [s for s in common if s in only_steps]
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    nd = 0
    worst = (0.0, None)
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
            nd += 1
            if d > worst[0]:
                worst = (d, '%s@step%s' % (c, s))
    print('  %-34s 共同步 %-10s 不同字段 %-5d 最大相对差 %.3e (%s) ⇒ %s'
          % (label, common, nd, worst[0], worst[1],
             '✅ 逐位相同' if nd == 0 else '❌ 有差异'))
    return nd == 0


def main():
    print('=' * 108)
    print('_r274 —— advance 并行不变性（`_r272` 的**部分**产物：step 0 / 20）')
    print('=' * 108)
    print('  ⚠ 记账：原计划 40 步，被工具超时打断 ⇒ 只有 step 0 与 20。')
    R = {t: rd(t) for t in ('th1', 'th2', 'th4', 'th8', 'th2b')}
    for t in R:
        print('  %-6s %s' % (t, ('%d 行，末步 %s' % (len(R[t]), R[t][-1]['step']))
                             if R[t] else '**缺失**'))
    print()
    ok = True
    print('  ## **T-1** 跨线程数（物理列）')
    ok &= cmp(R['th1'], R['th2'], 'th1 vs th2（1 vs 2 线程）')
    ok &= cmp(R['th1'], R['th4'], 'th1 vs th4（1 vs 4 线程）')
    print()
    print('  ## **T-2 负对照** 同线程数跑两次')
    ok &= cmp(R['th2'], R['th2b'], 'th2 vs th2b（都是 2 线程）')
    print()
    print('  ## **T-3** `th8`（只到 step 0）')
    if R['th8']:
        ok &= cmp(R['th1'], R['th8'], 'th1 vs th8（仅 step 0）', only_steps={'0'})
    else:
        print('     ⚠ th8 缺失')
    print()
    print('=' * 108)
    print('  ⇒ %s' % ('✅ **并行不变性在当前代码下成立**（step 0 与 20 上逐位相同）'
                       if ok else '❌ **有差异** ⇒ 须查'))
    print('  ⚠ **记账**：本判据只覆盖 step 0/20；**完整的 40 步复验未完成**（被打断）。')
    print('     若要更硬的结论，应重跑（**在无其他重负载时**、并给足超时）。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
