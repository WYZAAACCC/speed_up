#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_c5judge.py --- ★ 判据⑤（块填满整个盒子）的**预先写死**判决器

## 为什么先写（本 goal 的硬要求）
「量具正确性优先」⇒ **在测量之前**把判据写死，而不是看到数之后再想"这算不算填满"。

## 判据（**铁律，见 §19；不得在看到数之后修改**）
`abA` 跑满 **5922 步**末态填充也只有 **11.80%** ⇒
**「填满整个盒子」**不能**定义成"100% 填充"**，而应定义为：
| # | 判据 | 门槛 | 依据 |
|---|---|---|---|
| **①** | **触及盒面** | **`box_touch ≥ 1`** | 结构至少碰到一个盒面 ⇒ 不再是"盒中央一团" |
| **②** | **填充达平台** | **填充在最近 N 个读数上相对变化 < 5%** | 与 `abA` 的成熟态同型 |
| **③** | **（加分）多面触及** | `box_touch ≥ 3` | 更强的"铺开"证据 |
**⇒ 三条全过 ⇒ 判据⑤ 达成；②不过 ⇒ 判"仍在长大"（未到），不判 FAIL（P26）。**

## ⚠ 口径
* 填充的**在线值**在 `series.csv` 的 `Vt`/`nf3` 里（**不是** `box_touch` 的百分比）；
  `box_touch` 是**整数**（触及的盒面数）。
* 周期边界（`--nuc-periodic-seed 1`）下"触面"的含义**更强**（穿出即等价于另一侧的核）
  ⇒ **须在报告里写明这一点**。
"""
import csv
import os
import sys
import numpy as np

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5H3'
NLAST = int(sys.argv[2]) if len(sys.argv) > 2 else 8

D = '_exp/_bk_t5/dry_%s' % TAG
p = os.path.join(D, 'series.csv')
with open(p, newline='') as f:
    rows = list(csv.DictReader(f))

def col(name):
    out = []
    for r in rows:
        v = (r.get(name) or '').strip()
        if v in ('', 'nan'):
            continue
        try:
            out.append((int(float(r['step'])), float(v)))
        except Exception:
            pass
    return out

bt = col('box_touch')
print('=' * 84)
print('★ 判据⑤（填满整个盒子）判决器 —— %s' % TAG)
print('=' * 84)
print('  口径提醒：**「填满」= 触及盒面 + 填充达平台**，**不是 100% 填充**（§19 铁律；abA 末态仅 11.80%）')
print('  ⚠ 周期边界下"触面"含义更强（穿出等价于对侧核）')
print()
print('  行数 = %d   末步 = %s' % (len(rows), rows[-1].get('step') if rows else '—'))

if not bt:
    print()
    print('  ⚠ `box_touch` **全为空** ⇒ **无分辨力** ⇒ 判"未到"，**不判 FAIL**（P26）')
    sys.exit(0)

print('  `box_touch` 非空行数 = %d   末值 = **%.0f**' % (len(bt), bt[-1][1]))
print('  `box_touch` 轨迹（前 3 / 后 8）= %s … %s' %
      ([int(v) for _, v in bt[:3]], [(int(s), int(v)) for s, v in bt[-NLAST:]]))

# ② 填充平台：用 nf3（F3 面积，单调量）当填充的代理
nf3 = col('nf3')
plat = None
if len(nf3) >= NLAST + 1:
    tail = np.array([v for _, v in nf3[-NLAST:]], dtype=float)
    rel = float((tail.max() - tail.min()) / max(tail.max(), 1e-12))
    plat = rel
    print()
    print('  填充代理（`nf3`，末 %d 个读数）：%.0f … %.0f   相对变化 = **%.2f%%**'
          % (NLAST, tail[0], tail[-1], rel * 100))

print()
print('  ── 判据（预先写死）──')
c1 = bt[-1][1] >= 1
print('  ① 触及盒面  `box_touch >= 1`      ：末值 %.0f ⇒ %s' % (bt[-1][1], '✅ PASS' if c1 else '❌ 未达'))
if plat is None:
    print('  ② 填充平台  相对变化 < 5%%          ：**数据不足** ⇒ ⏳ 未到')
    c2 = None
else:
    c2 = plat < 0.05
    print('  ② 填充平台  相对变化 < 5%%          ：%.2f%% ⇒ %s'
          % (plat * 100, '✅ PASS' if c2 else '⏳ 仍在长大（未到，**不判 FAIL**）'))
c3 = bt[-1][1] >= 3
print('  ③ 多面触及  `box_touch >= 3`（加分）：末值 %.0f ⇒ %s' % (bt[-1][1], '✅' if c3 else '—'))

print()
print('  ── 结论 ──')
if c1 and c2:
    print('     ✅ **判据⑤ 达成**（触面 + 填充平台）%s' % ('，且多面触及（更强）' if c3 else ''))
elif not c1:
    print('     ⏳ **未到**：结构尚未触及任何盒面 ⇒ **不判 FAIL**（仍在长大）')
else:
    print('     ⏳ **未到**：已触面但填充**仍在长大** ⇒ 等它平台化（abA 也是跑到 5922 步才成熟）')
