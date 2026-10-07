#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r316_edscale.py —— 框架级问题：**`ed` 的离散度是否随"变体表的应变差异"变化？**

## 动机（objective 第 (2) 部分："检查协调框架是否完善"）
`ed_v = Σ_p e0v_eng[v,p]·σ_p + sext_e0[v]` —— 这是变体 v 与**局部应力**的**自项**。
**没有显式的"变体-变体弹性相互作用"项**；相互作用只经**共享的 σ** 间接发生
（这是标准的平均场做法）。
⇒ **关键问题**：σ 到底**响应不响应"变体配置"**？
* 若响应 ⇒ `ed` 会编码变体间相互作用 ⇒ 自协调**可能**自发出现；
* 若不响应（σ 被别的东西主导）⇒ `ed` 无法区分变体 ⇒ **`§146`/`§148` 的"中性"就有了解释**。

## 本脚本能做的（**只用已有数据**）
比较两个 `--diag-edv` 臂在**相同 step** 上的 `ed` **离散度**：
* **A `saSet2EDV`**：变体集 `{1,2,3,4,7,8}`（**6 个**），N=112，`plate-L` 1000
* **B `mb2fp10EDV`**：变体集 `{1,3}`（**2 个**），N=96，`plate-L` 1600

**预言**：若 σ 响应变体配置，则**变体越多 ⇒ `ed` 离散度越大**。

⚠ **本比较有多个混杂**（N、块数、`plate-L`、步长都不同）⇒ **只能作"提示性"证据**，
**不作结论**（硬规则 ㉞ / ㉟ 的精神）。
"""
from __future__ import annotations

import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RE_F = re.compile(r'场(\d+)\s+V(\d+)\s+体积\s+([\d.]+)\s+µm³\s+`ed` 中位 \*\*([-+\d.eE]+)\*\*')
RE_H = re.compile(r'逐变体 `ed`\*\*（`§135\.6`）@step (\d+)')


def parse(path):
    if not os.path.exists(path):
        return {}
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    parts = RE_H.split(txt)
    out = {}
    for i in range(1, len(parts), 2):
        step = int(parts[i])
        meds = [float(m.group(4)) for m in RE_F.finditer(parts[i + 1])]
        if meds:
            a = np.asarray(meds, float)
            out[step] = dict(n=len(meds), spread=float(a.max() - a.min()),
                             std=float(a.std()))
    return out


def main():
    print('=' * 100)
    print('_r316 —— `ed` 的离散度：变体多的构型是否更大？（**含混杂，只作提示**）')
    print('=' * 100)
    A = parse(os.path.join(HERE, '_w2_r240_run.log'))    # 6 变体
    B = parse(os.path.join(HERE, '_w2_r311_run.log'))    # 2 变体
    print('  A `saSet2EDV`   6 变体 / 12 场 / N=112 / plate-L 1000：%d 个 step' % len(A))
    print('  B `mb2fp10EDV`  2 变体 /  6 场 / N= 96 / plate-L 1600：%d 个 step' % len(B))
    common = sorted(set(A) & set(B))
    print()
    print('  ## 相同 step 上的 `ed` 离散度')
    print('     %-6s %-6s %-14s %-14s %s'
          % ('step', '场数', 'A 极差(6变体)', 'B 极差(2变体)', 'A/B'))
    rs = []
    for s in common:
        r = A[s]['spread'] / B[s]['spread'] if B[s]['spread'] else float('nan')
        rs.append(r)
        print('     %-6d %d/%d   %-14.4e %-14.4e %.2f×'
              % (s, A[s]['n'], B[s]['n'], A[s]['spread'], B[s]['spread'], r))
    print()
    if rs:
        print('     ⇒ 比值 中位 = **%.2f×**（范围 %.2f – %.2f）'
              % (float(np.median(rs)), min(rs), max(rs)))
        print('     ⇒ %s' % ('**变体多的构型 `ed` 离散度更大**（提示 σ 响应变体配置）'
                             if np.median(rs) > 1.2 else
                             '两者相当（提示 σ **不**因变体数而变）'))
    print()
    print('  ## ⚠⚠ 混杂清单（**本比较不能作结论的原因**）')
    print('     | 因素 | A | B |')
    print('     |---|---|---|')
    print('     | 变体数 | **6** | **2** |')
    print('     | 场数 | 12 | 6 |')
    print('     | N | **112** | **96** |')
    print('     | `plate-L` [nm] | **1000** | **1600** |')
    print('     | 块数 × 每块根数 | 6 × 2 | 2 × 3 |')
    print('     ⇒ **至少 5 个因素同时不同** ⇒ **不是单变量** ⇒ **不能归因给"变体数"**。')
    print()
    print('  ⚠ 记账：要**真正**回答"σ 响应不响应变体配置"，必须做**单变量**实验：')
    print('     同几何、同 N、同 `plate-L`、同块布局，**只换变体集**（例如 `{1,3}` vs `{1,2,3,4,7,8}`）。')
    print('     ⇒ **列为待办**（本轮不做）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
