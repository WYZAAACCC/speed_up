#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vtstep.py <tagA> <tagB> —— **同一 `Vt` 所需步数比**（检验"是否改动力学"）。

## 为什么做（`R673 §3`）
`R649` 对 `facet_proj` 就是这么做的（结论：达到同一 `Vt` 只需 **1/2.27** 的步数
⇒ **它改动力学**）。本工具对 `mob_dip` 做同一件事：
**若 `W4` 与 `W0` 在同一 `Vt` 上所需步数接近（比值 ≈1）⇒ `mob_dip` 不改动力学**（推论成立）；
**若比值远离 1 ⇒ 我的推断被推翻**（须记账）。

## 判据（可 FAIL，先登记）
| 量 | 判据 |
|---|---|
| 达到同一 `Vt` 的步数比 `N(W0)/N(W4)` | **0.8 – 1.25 ⇒ "不改动力学"成立**；否则推翻 |

⚠ 口径（`P30`）：`Vt` 在 CSV 里的单位与横幅不同，本工具**只用 CSV 内部一致的列**。
"""
import csv
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
TAGS = sys.argv[1:] or ["W0", "W4"]


def series(tag):
    p = os.path.join(ROOT, "dry_%s" % tag, "series.csv")
    if not os.path.exists(p):
        return None
    st, vt = [], []
    with open(p, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                s = int(r["step"])
                v = float(r.get("Vt") or "nan")
            except (KeyError, ValueError):
                continue
            if v == v and v > 0:
                st.append(s)
                vt.append(v)
    if not st:
        return None
    return np.array(st), np.array(vt)


D = {}
for t in TAGS:
    s = series(t)
    if s is None:
        print("  ⚠ %s 无可用 Vt 数据" % t)
        continue
    D[t] = s
    print("  %-6s step %d..%d，Vt %.4g .. %.4g m³" % (t, s[0][0], s[0][-1], s[1][0], s[1][-1]))
if len(D) < 2:
    sys.exit(1)

A, B = TAGS[0], TAGS[1]
sa, va = D[A]
sb, vb = D[B]
# 用 A 的 Vt 序列作靶，反查 B 达到同一 Vt 的 step（线性插值）
print()
print("=" * 92)
print("同一 `Vt` 所需步数对照（`%s` 为靶，反查 `%s`）" % (A, B))
print("=" * 92)
print("  %-8s %-14s %-14s %-12s %s" % ('靶 Vt (m³)', 'step(%s)' % A, 'step(%s)' % B, '比值 A/B', '判定'))
ratios = []
for i in range(0, len(va), max(1, len(va) // 12)):
    v0 = va[i]
    if v0 > vb.max() or v0 < vb.min():
        continue
    s_b = float(np.interp(v0, vb, sb))
    r = sa[i] / max(s_b, 1e-9)
    ratios.append(r)
    ok = '✅ 不改动力学' if 0.8 <= r <= 1.25 else ('⛔ **改动力学**（B 快 %.2fx）' % (1 / r) if r > 1.25 else '⚠ B 更慢')
    print("  %-8.4g %-14d %-14.0f %-12.3f %s" % (v0, sa[i], s_b, r, ok))
print()
if ratios:
    m = float(np.median(ratios))
    print("  ⇒ **比值中位 = %.3f**（%d 个配对点）" % (m, len(ratios)))
    print("  ⇒ 判定：%s" % ('✅ **`%s` 不改动力学**（落在 0.8–1.25）' % B if 0.8 <= m <= 1.25
                            else '⛔ **`%s` **改**动力学**（比值 %.3f 超出 0.8–1.25）⇒ 我的推断被推翻' % (B, m)))
