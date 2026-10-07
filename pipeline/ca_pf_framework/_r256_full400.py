#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r256_full400.py —— `saSet2DT`（**跑满 400 步**）的两项分析：

## ① 全程惰性（**比回归更强的一条**）
`saSet2DT` = 归档 `dry_saSet2` 的**逐参重建** + **只多一个 `--diag-terms`**（纯只读）。
⇒ 若末态逐位相同 ⇒ **该诊断开关在**完整 400 步**上也不扰动结果**
（`§133` 只证了 120 步；`_r30_regress` 只跑了 200 步的 `eng12` 臂）。

## ② 三类界面的**全程**画像（`§141.1` 的完整版）
引擎诊断给 `(karr,larr)` 配对口径的胞数/比值；配合 `§142.1` 的
`region` 几何口径面积占比，给出 400 步的完整结论。
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def part1():
    print('=' * 108)
    print('① 全程惰性：`saSet2DT`（新代码 + `--diag-terms`）vs 归档 `saSet2`')
    print('=' * 108)
    A, B = rows('saSet2DT'), rows('saSet2')
    if A is None or B is None:
        print('  ⚠ 缺数据')
        return
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    print('  共同步 %d 个（%s … %s）；可比列' % (len(common), common[0], common[-1]), end='')
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    print(' %d 个' % len(cols))
    diff = []
    for c in cols:
        worst = 0.0
        n_same = 0
        for s in common:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                if (sa[s].get(c) or '') == (sb[s].get(c) or ''):
                    n_same += 1
                continue
            if fa != fa and fb != fb:
                n_same += 1
                continue
            if repr(fa) == repr(fb):
                n_same += 1
                continue
            worst = max(worst, abs(fa - fb) / max(abs(fa), abs(fb), 1e-300))
        if n_same != len(common):
            diff.append((c, worst))
    print()
    print('  ## 逐位相同的列 = **%d / %d**' % (len(cols) - len(diff), len(cols)))
    if diff:
        print('  ## 有差异的列（%d 个）' % len(diff))
        for (c, w) in sorted(diff, key=lambda d: -d[1])[:15]:
            print('     %-24s 最大相对差 %.3e' % (c, w))
    else:
        print('  ⇒ ✅ **全部 %d 列、%d 个共同步逐位相同** ⇒ '
              '`--diag-terms` 在**完整 400 步**上惰性' % (len(cols), len(common)))
    print('  ⚠ 新列（归档没有的）不参与比较：%s'
          % [c for c in A[0] if c not in B[0]][:12])


def part2():
    print()
    print('=' * 108)
    print('② `saSet2DT` 全程三类界面画像（引擎诊断口径 `(karr,larr)`）')
    print('=' * 108)
    p = os.path.join(HERE, '_w2_r210_saSet2_run.log')
    if not os.path.exists(p):
        print('  ⚠ 无日志')
        return
    txt = io.open(p, encoding='utf-8', errors='replace').read()
    blocks = re.split(r'★★ \*\*三项量级\*\*（`§135\.7`）@step (\d+)', txt)
    recs = []
    for i in range(1, len(blocks), 2):
        step = int(blocks[i]); body = blocks[i + 1]
        rec = {'step': step}
        for lab, key in (('F2 异变体', 'f2'), ('F3 同变体', 'f3'), ('F1 含母相', 'f1')):
            m = re.search(re.escape(lab) + r'\s+胞数\s+(\d+)\s+`\|Δed\|` 中位 \*\*([\d.eE+-]+)\*\*'
                          r'（`Δed`≡0 占 ([\d.]+)%）\s+`\|stk·κ\|` 中位 \*\*([\d.eE+-]+)\*\*'
                          r'\s+\*\*比值中位 ([\d.]+)%\*\*', body)
            rec[key] = dict(n=int(m.group(1)), med_ed=float(m.group(2)),
                            f0=float(m.group(3)), med_sk=float(m.group(4)),
                            ratio=float(m.group(5))) if m else \
                dict(n=int(re.search(re.escape(lab) + r'\s+胞数\s+(\d+)', body).group(1)))
        recs.append(rec)
    print('  共 %d 条记录（step %s … %s）'
          % (len(recs), recs[0]['step'], recs[-1]['step']))
    print()
    print('  %-5s | %-26s | %-26s | %s'
          % ('step', 'F2 异变体（胞数/比值）', 'F3 同变体（胞数/比值）', 'F1 含母相（胞数/比值）'))
    for r in recs[::max(1, len(recs) // 10)] + [recs[-1]]:
        def fmt(d):
            if 'ratio' in d:
                return '%6d  %7.2f%%  (Δed≡0 %4.1f%%)' % (d['n'], d['ratio'], d['f0'])
            return '%6d  （不足）' % d['n']
        def fmt1(d):
            return ('%6d  %8.3f%%' % (d['n'], d['ratio'])) if 'ratio' in d \
                else '%6d  （不足）' % d['n']
        print('  %-5d | %-26s | %-26s | %s'
              % (r['step'], fmt(r['f2']), fmt(r['f3']), fmt1(r['f1'])))
    print()
    last = recs[-1]
    n1, n2, n3 = last['f1']['n'], last['f2']['n'], last['f3']['n']
    tot = n1 + n2 + n3
    print('  ## 末步（400）三类**胞数**占比（引擎口径，≈ 面积占比）')
    print('     F1 **%.1f%%**  F2 **%.1f%%**  F3 **%.1f%%**'
          % (100 * n1 / tot, 100 * n2 / tot, 100 * n3 / tot))
    if 'ratio' in last['f2']:
        print('     F2 的 `|stk·κ|/|Δed|` 中位 = **%.2f%%**（Δed≡0 占 %.1f%%）'
              % (last['f2']['ratio'], last['f2']['f0']))
    if 'ratio' in last['f3']:
        print('     F3 的 `|stk·κ|/|Δed|` 中位 = **%.2f%%**（Δed≡0 占 %.1f%%）'
              % (last['f3']['ratio'], last['f3']['f0']))
    else:
        print('     ⚠ **F3 全程胞数不足** ⇒ 引擎口径下 F3 从未成立（见 `§142.2` 的口径说明）')


if __name__ == '__main__':
    part1()
    part2()
    sys.exit(0)
