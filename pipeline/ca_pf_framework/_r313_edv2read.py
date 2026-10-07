#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r313_edv2read.py —— ★ **`§146`/`§148` 的多构型检验**：`ed` 到底按位置还是按变体组织？

## 背景（硬规则 ㉞ 的追溯应用）
`§146`/`§148` 的"**`ed` 按场/位置组织、不按变体**"（变体内/变体间 = **0.887**）
**只基于 1 个构型**（`saSet2`：6 块 × 2 根、6 个变体）。
⇒ 本节用**真正不同的**构型复核：**`mb2fp10`**（**2 块 × 3 根**、**2 个变体**、N=96）。

**★ 为什么这个构型是**更严格**的检验**：
每块 **3 根**（`saSet2` 是 2 根）⇒ 每个变体有 **3 个场**
⇒ "变体内离散"有 **3 个样本**（而非 2）⇒ 更不容易被偶然压低。

## 判据（**先写死**）
* **E-1** 对同一 step，算 **`比 = 变体内最大极差 / 变体间极差`**。
* **E-2** 与 `saSet2EDV`（构型 A）在**相同 step 上**对比：
  * 若构型 B 的比值**也 ≈ 1**（例如 0.5–2）⇒ **`§146` 稳健**；
  * 若构型 B 的比值 **≪ 1**（例如 <0.3）⇒ **须收窄**：`ed` 在"每块根数多"时**确实按变体组织**。
* **E-3** 同时报 `ed` 中位的**极差**与**标准差**（跨场），以及各变体的**体积**。
* **E-4** 退化：某变体只有 1 个场 ⇒ within 记为 0 并**说明**（不算作证据）。
"""
from __future__ import annotations

import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

RE_F = re.compile(
    r'场(\d+)\s+V(\d+)\s+体积\s+([\d.]+)\s+µm³\s+`ed` 中位 \*\*([-+\d.eE]+)\*\*')
RE_S = re.compile(r'⇒ 跨变体：`ed` 中位的\*\*极差 ([-+\d.eE]+)\*\*、'
                  r'\*\*标准差 ([-+\d.eE]+)\*\*（均值 ([-+\d.eE]+)）；体积 CV = ([\d.]+)')
RE_H = re.compile(r'逐变体 `ed`\*\*（`§135\.6`）@step (\d+)')


def parse(path):
    if not os.path.exists(path):
        return {}
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    parts = RE_H.split(txt)
    out = {}
    for i in range(1, len(parts), 2):
        step = int(parts[i])
        body = parts[i + 1]
        fields = [dict(field=int(m.group(1)), variant=int(m.group(2)),
                       vol=float(m.group(3)), med=float(m.group(4)))
                  for m in RE_F.finditer(body)]
        s = RE_S.search(body)
        summ = dict(spread=float(s.group(1)), std=float(s.group(2)),
                    vol_cv=float(s.group(4))) if s else {}
        if fields:
            out[step] = dict(fields=fields, **summ)
    return out


def analyse(rec):
    """返回 (ratio, within_max, between, note)。"""
    byv = {}
    for f in rec['fields']:
        byv.setdefault(f['variant'], []).append(f['med'])
    within, skip = [], []
    for var, meds in sorted(byv.items()):
        if len(meds) > 1:
            within.append(max(meds) - min(meds))
        else:
            skip.append(var)
    allm = np.array([f['med'] for f in rec['fields']], float)
    between = float(allm.max() - allm.min())
    if not within or between <= 0:
        return float('nan'), float('nan'), between, \
            ('每变体仅 1 个场 ⇒ **不适用**' if skip else '**退化**')
    wmax = float(max(within))
    return wmax / between, wmax, between, ''


def main():
    print('=' * 108)
    print('_r313 —— `§146`/`§148` 的多构型检验：`ed` 按位置还是按变体？')
    print('=' * 108)
    A = parse(os.path.join(HERE, '_w2_r240_run.log'))          # 构型 A：saSet2EDV
    B = parse(os.path.join(HERE, '_w2_r311_run.log'))          # 构型 B：mb2fp10EDV
    print('  构型 A `saSet2EDV`（6 块 × 2 根、6 变体、N=112）：%d 个 step 点'
          % len(A))
    print('  构型 B `mb2fp10EDV`（**2 块 × 3 根**、**2 变体**、N=96）：%d 个 step 点'
          % len(B))
    if not B:
        print('\n  ⚠ 构型 B 还没有输出（该打印在 `it % every == 0` 时触发）⇒ 稍后再读')
        return 2
    print()
    print('  ## **E-1/E-2** 逐 step 的"变体内 / 变体间"')
    print('     %-6s | %-34s | %s'
          % ('step', 'A: saSet2EDV（6 块×2 根）', 'B: **mb2fp10EDV（2 块×3 根）**'))
    print('     %-6s | %-34s | %s' % ('', '比    变体内    变体间', '比    变体内    变体间'))
    ratios = {'A': [], 'B': []}
    for s in sorted(set(A) | set(B)):
        ra, wa, ba, na = analyse(A[s]) if s in A else (float('nan'),) * 4
        rb, wb, bb, nb = analyse(B[s]) if s in B else (float('nan'),) * 4
        if s in A:
            ratios['A'].append(ra)
        if s in B:
            ratios['B'].append(rb)
        # ★ 修（**第 28 个自查错误**）：原来写 `('  ' + nb) if nb else ''` ——
        #   当 `nb` 是**非空字符串**时 OK，但 `analyse` 在"不适用"路径返回的是
        #   **字符串**、在"退化"路径也可能返回 `nan`（float）⇒
        #   非空 float 会走 `'  ' + nb` ⇒ `TypeError: can only concatenate str`。
        #   ⇒ 显式转成 str。
        _na = ('  ' + str(na)) if na else ''
        _nb = ('  ' + str(nb)) if nb else ''
        print('     %-6d | %-9.3f %-9.3e %-9.3e | %-9.3f %-9.3e %-9.3e%s%s'
              % (s, ra, wa, ba, rb, wb, bb, _nb, _na))
    print()
    print('  ## **E-3** 汇总')
    for lab, r in (('A `saSet2EDV`', ratios['A']), ('B `mb2fp10EDV`', ratios['B'])):
        r = [x for x in r if x == x]
        if r:
            print('     %-18s 比值的 中位 = **%.3f**（范围 %.3f – %.3f，%d 个点）'
                  % (lab, float(np.median(r)), min(r), max(r), len(r)))
        else:
            print('     %-18s （无可用的点）' % lab)
    print()
    rb = [x for x in ratios['B'] if x == x]
    if rb:
        medB = float(np.median(rb))
        print('  ## **E-2** 判定（构型 B 的比值中位 = %.3f）' % medB)
        if medB >= 0.5:
            print('     ⇒ ✅ **`§146` 稳健**：换构型后"变体内 ≈ 变体间"仍成立'
                  ' ⇒ `ed` 按位置组织是**跨构型**现象')
        else:
            print('     ⇒ ⚠ **须收窄 `§146`**：在该构型上变体内**明显小于**变体间'
                  ' ⇒ `ed` 在"每块根数多"时**确实按变体组织**')
    else:
        print('     ⇒ ⚠ 构型 B 还没有可判定的 step 点')
    print()
    print('  ⚠ 记账：`ed` 中位是**各自场领土上**的中位（`§148.2`）；')
    print('     比值为 1 表示"同变体两场差得不比不同变体少"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
