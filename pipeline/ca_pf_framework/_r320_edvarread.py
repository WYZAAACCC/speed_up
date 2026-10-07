#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r320_edvarread.py —— ★★ **框架级判决**：σ 响应不响应"变体配置"？

## 判据（`_r318` 头部已写死）
三臂**几何逐字相同**（N=96 / `plate-L 1600` / `1,1,1,x,x,x` / `--multi-block` /
`facet-proj 10` / 60 步 / `--diag-edv`），**只改 `x`**：

| 臂 | `--laths` | 变体对 | `‖ε⁰₁ − ε⁰_w‖_F` | 相对基准 |
|---|---|---|---|---|
| `edNear` | `1,1,1,2,2,2` | V1–V2 | **0.025990** | **0.21×** |
| `mb2fp10EDV` | `1,1,1,3,3,3` | V1–V3 | **0.123728** | 1.00× |
| `edFar` | `1,1,1,5,5,5` | V1–V5 | **0.242277** | **1.96×** |

* **P-2 ★ 核心**：三臂在相同 step 上的 `ed` **离散度**。
  * **预言**：若 σ 响应变体配置 ⇒ 离散度随 `‖Δε‖` **单调增**；
  * **若都与 `‖Δε‖` 无关** ⇒ **σ 不由变体配置主导** ⇒
    这就**从框架层**解释了"为什么没有自协调"。
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

ARMS = [('edNear', '1,1,1,2,2,2', 0.025990),
        ('mb2fp10EDV', '1,1,1,3,3,3', 0.123728),
        ('edFar', '1,1,1,5,5,5', 0.242277)]


def parse(path):
    if not os.path.exists(path):
        return {}
    txt = io.open(path, encoding='utf-8', errors='replace').read()
    parts = RE_H.split(txt)
    out = {}
    for i in range(1, len(parts), 2):
        step = int(parts[i])
        meds = [float(m.group(4)) for m in RE_F.finditer(parts[i + 1])]
        if len(meds) >= 2:
            a = np.asarray(meds, float)
            out[step] = dict(n=len(meds), spread=float(a.max() - a.min()),
                             std=float(a.std()))
    return out


def main():
    print('=' * 104)
    print('_r320 —— 框架级判决：σ 响应不响应"变体配置"？')
    print('=' * 104)
    D = {}
    for (tag, lat, de) in ARMS:
        p = os.path.join(HERE, '_w2_r318_%s_run.log' % tag) if tag != 'mb2fp10EDV' \
            else os.path.join(HERE, '_w2_r311_run.log')
        D[tag] = parse(p)
        print('  %-14s `--laths %-16s ‖Δε‖=%.6f  ⇒ %d 个 step 点'
              % (tag, lat + '`', de, len(D[tag])))
    common = sorted(set.intersection(*[set(D[t]) for (t, _, _) in ARMS]))
    if not common:
        print('\n  ⚠ 三臂没有共同 step（可能还没跑出 step 20）⇒ 稍后再读')
        return 2
    print()
    print('  ## **P-2** 相同 step 上的 `ed` 离散度')
    print('     %-6s | %-22s | %-22s | %s'
          % ('step', 'edNear (‖Δε‖=0.0260)', 'mb2fp10EDV (0.1237)',
             'edFar (0.2423)'))
    print('     %-6s | %-10s %-11s | %-10s %-11s | %s'
          % ('', '极差', '标准差', '极差', '标准差', '极差  标准差'))
    for s in common:
        a, b, c = D['edNear'][s], D['mb2fp10EDV'][s], D['edFar'][s]
        print('     %-6d | %-10.4e %-11.4e | %-10.4e %-11.4e | %.4e %.4e'
              % (s, a['spread'], a['std'], b['spread'], b['std'],
                 c['spread'], c['std']))
    print()
    print('  ## 判定：离散度是否随 `‖Δε‖` 单调增？')
    mono_sp, mono_sd = 0, 0
    for s in common:
        sp = [D[t][s]['spread'] for (t, _, _) in ARMS]
        sd = [D[t][s]['std'] for (t, _, _) in ARMS]
        oks = all(sp[i] <= sp[i + 1] * 1.0000001 for i in range(len(sp) - 1))
        okd = all(sd[i] <= sd[i + 1] * 1.0000001 for i in range(len(sd) - 1))
        mono_sp += oks
        mono_sd += okd
        print('     step %-5d 极差 %s（%.3e → %.3e → %.3e）；标准差 %s'
              % (s, '**单调增**' if oks else '非单调', sp[0], sp[1], sp[2],
                 '**单调增**' if okd else '非单调'))
    print()
    print('     ⇒ 极差单调增的 step 数 = **%d / %d**；标准差 = **%d / %d**'
          % (mono_sp, len(common), mono_sd, len(common)))
    if mono_sp == len(common) or mono_sd == len(common):
        print('     ⇒ ✅ **观察到单调关系** ⇒ 提示 σ **响应**变体配置')
        print('        ⚠ 但只有 3 个构型、1 个时间窗 ⇒ 只作**提示**，不作定论')
    else:
        print('     ⇒ ❌ **离散度与 `‖Δε‖` 无关**（不单调）')
        print('        ⇒ ⇒ **σ 不由变体配置主导** —— 这从**框架层**解释了')
        print('           「为什么没有自协调」：`ed` 分不出变体，')
        print('           与 `§146`/`§148`（`ed` 按位置组织）**互相印证**。')
    print()
    print('  ⚠ 记账：三臂**只差 `--laths`**（其余逐字相同，由 `_r318` 的 sed 保证）；')
    print('     但 `‖Δε‖` 是**本征应变的差**，改变体也会轻微改变**块内低角界面的 θ**')
    print('     （`ω` 按序号给，与变体无关 ⇒ **这一项三臂相同** ✓）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
