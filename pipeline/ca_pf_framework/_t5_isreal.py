#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_isreal.py --- ⚠⚠⚠ **量具正确性**检验：板条退化是**真实**发生的吗？

## 为什么必须先做这一步（**用户明确要求"注意量具的正确性"**）
我先前测"板条缩短/消失"，用的是快照里的 **`region`**。
**但 `region = argmin(φ)` 是**归属标签**，不是**物理相**：**
```
一个格点可以有 `φ_k < 0`（确实是场 k 的相），却因 `φ_0` 更低而被标成 0（母相）
⇒ ⇒ **"region 里少了" 不等于 "相消失了"** —— 我的量具**可能整体偏错**。
```
**★ 而快照里**根本没有存 φ****（键只有：`region` / `band_*` / `n_hab` / `vmap_*` …）
⇒ ⇒ **无法从快照直接算"相的体积"** ⇒ **这是一个**量具局限**，必须记账。**

## 因此改用**不依赖归属的硬量**：引擎自报的 `Vt`（已转变体积，`series.csv`）
**判据（**预先写死**）：**
| `Vt(t)` 的行为 | 结论 |
|---|---|
| **单调不减** | **没有净溶解** ⇒ 我先前测的"缩短/消失"是**归属重排**（表示层）⇒ **退化不是真实的** |
| **出现下降** | **确有净溶解** ⇒ 退化**是真实的** ⇒ 需继续查物理/代码 |

**同时报**：`Vt` 的**最大单步跌幅**与**出现跌幅的步点**（若有）。
"""
import csv
import os
import sys

TAG = sys.argv[1] if len(sys.argv) > 1 else 't5N276F'
P = '_exp/_bk_t5/dry_%s/series.csv' % TAG
if not os.path.exists(P):
    print('  ⚠ 无 %s' % P); sys.exit(1)

rows = []
for r in csv.DictReader(open(P, newline='')):
    try:
        rows.append((int(r['step']), float(r['Vt'])))
    except Exception:
        pass
if not rows:
    print('  ⚠ 无有效行'); sys.exit(1)

print('=' * 96)
print('★ %s：`Vt`（已转变体积）的单调性检验 —— 判"退化是否真实"' % TAG)
print('=' * 96)
print('  步数 = %d ｜ step %d → %d' % (len(rows), rows[0][0], rows[-1][0]))
print('  Vt 首 = %.6f µm³   末 = %.6f µm³   净增 %.6f µm³'
      % (rows[0][1] * 1e18, rows[-1][1] * 1e18, (rows[-1][1] - rows[0][1]) * 1e18))

drops = []
for i in range(1, len(rows)):
    d = rows[i][1] - rows[i - 1][1]
    if d < -1e-12:
        drops.append((rows[i][0], d, rows[i - 1][1], rows[i][1]))
print()
if not drops:
    print('  ✅ **Vt 单调不减（零次下降）**')
    print('  ⇒ ⇒ **没有净溶解 ⇒ 我先前测的"板条缩短/消失"是**归属重排**（表示层），')
    print('     不是物理退化** ⇒ **"退化"这个判断需要重新表述。**')
else:
    print('  ❌ **Vt 出现 %d 次下降**（净溶解确实存在）' % len(drops))
    mx = min(drops, key=lambda t: t[1])
    print('     最大单步跌幅：step %d  %.6f → %.6f µm³（**%.4f%%**）'
          % (mx[0], mx[2] * 1e18, mx[3] * 1e18, 100.0 * mx[1] / max(mx[2], 1e-30)))
    print('     前 8 次下降：')
    for st, d, a, b in drops[:8]:
        print('        step %-6d %.6f → %.6f µm³（%.4f%%）'
              % (st, a * 1e18, b * 1e18, 100.0 * d / max(a, 1e-30)))
    print('  ⇒ **确有净溶解 ⇒ 退化是真实的** ⇒ 需继续查物理框架与代码。')

print()
print('  ── ⚠ 量具局限（**必须记账**）──')
print('  * 快照**不存 φ**（只有 `region`）⇒ **无法从快照直接算"相的体积"**;')
print('  * `Vt` 是**全盒**量 ⇒ 它**能**判"有没有净溶解"，但**不能**判"是哪根板条溶解";')
print('  * ⇒ 若要**逐场**判溶解，必须**让引擎在快照里存 `phi`**（或逐场存 φ<0 的胞数）——')
print('    **这是量具的缺口，不是数据的缺口**（引擎内存着 φ，只是没落盘）。')
