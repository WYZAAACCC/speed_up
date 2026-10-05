#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_wrapchk2.py --- ★ 按**框架自己的口径**判「绕盒」（不是我自己发明的 P1）

## 框架的口径（`windowB_surface.py:3354-3357` 的原话）
```
def wrap_axes(self, k=None):
    为什么必须有：周期边界下，**长过 L/2 的板条会绕盒**，其"长度"读数会超过 L
```
⇒ 判据是 **沿轴的跨度 > L/2**（比"同时触及两个相对面"**更早触发**）。

## 本脚本做什么
对快照里每个场，沿三个盒轴分别算：
* `span`：该场胞的**包围盒跨度**
* `touch2`：是否**同时**触及该轴的两个相对面（我上一轮的 P1，较弱）
* `gt_half`：`span > L/2`（**框架口径**，较强）
并把 `gt_half` 的场列为「按框架口径已绕盒」。

## 正对照（必须）
`span` 的**量具自检**：对合成的一根**已知跨度为 s 的直线**算 span，应得 s。
另：断言 `gt_half` 的集合 ⊇ 由 `touch2` 判出的集合之外还可能有更多（口径更严）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TAG = sys.argv[1] if len(sys.argv) > 1 else "t10PRT2_b3_1005_1213"
ST = int(sys.argv[2]) if len(sys.argv) > 2 else 100
p = os.path.join(HERE, "_exp/_bk_t5/dry_%s/snap_%05d.npz" % (TAG, ST))
with np.load(p, allow_pickle=False) as z:
    N = int(np.asarray(z["N"]))
    bi = np.asarray(z["band_idx"]).ravel().astype(np.int64)
    bv = np.asarray(z["band_val"]).ravel()
    bf = np.asarray(z["band_fld"]).ravel()
DX = 62.5e-9
L = N * DX
print("══ 绕盒判定（框架口径：span > L/2）  %s step=%d ══" % (TAG, ST))
print("  N=%d  dx=%.1f nm  L=%.3f µm  L/2=%.3f µm\n" % (N, DX * 1e9, L * 1e6, L * 1e6 / 2))

# ---- 正对照：span 量具 ----
g = np.zeros((N, N, N), bool)
s0 = 37
g[10, 20, 30:30 + s0] = True
ax_idx = np.argwhere(g)
span0 = (ax_idx.max(0) - ax_idx.min(0) + 1)[2] * DX
ok = abs(span0 - s0 * DX) < 1e-12
print("  正对照：合成直线 37 胞 ⇒ span = %.4f µm ，期望 %.4f µm  %s"
      % (span0 * 1e6, s0 * DX * 1e6, "✅" if ok else "❌ FAIL"))
if not ok:
    sys.exit(1)

rows = []
for k in np.unique(bf[bv < 0]):
    k = int(k)
    if k == 0:
        continue
    sel = (bf == k) & (bv < 0)
    if sel.sum() < 30:
        continue
    idx = bi[sel]
    ijk = np.stack([idx // (N * N), (idx // N) % N, idx % N], 1)
    lo, hi = ijk.min(0), ijk.max(0)
    spans = (hi - lo + 1) * DX
    touch2 = []
    gt_half = []
    for a, nm in enumerate("xyz"):
        if lo[a] == 0 and hi[a] == N - 1:
            touch2.append(nm)
        if spans[a] > L / 2:
            gt_half.append(nm)
    rows.append((k, spans, touch2, gt_half))

n_t2 = sum(1 for r in rows if r[2])
n_gh = sum(1 for r in rows if r[3])
print("\n  参与统计的场 = %d" % len(rows))
print("  ★ 同时触及两个相对面（我上一轮的 P1，弱）      = **%d** 个" % n_t2)
print("  ★ span > L/2（**框架口径**，强）              = **%d** 个" % n_gh)
print()
print("  %-6s %-26s %-10s %s" % ("场", "三轴跨度 (µm)", "touch2", "span>L/2"))
for k, spans, t2, gh in sorted(rows, key=lambda r: -max(r[1]))[:14]:
    print("  %-6d %-26s %-10s %s"
          % (k, " ".join("%.2f" % (s * 1e6) for s in spans),
             ",".join(t2) or "-", ",".join(gh) or "-"))

# 最大跨度分布
mx = np.array([max(r[1]) for r in rows])
print("\n  各场**最大轴跨度**（µm）：min=%.2f  中位=%.2f  max=%.2f  ；L/2=%.2f"
      % (mx.min() * 1e6, np.median(mx) * 1e6, mx.max() * 1e6, L * 1e6 / 2))
n_exceed = int((mx > L / 2).sum())
print("  ★ 最大跨度 > L/2 的场 = **%d / %d = %.0f%%**"
      % (n_exceed, len(rows), 100.0 * n_exceed / len(rows)))
if n_gh > 0:
    print("\n  ⇒ **按框架口径已有 %d 个场绕盒** ⇒ 「板条长出盒子」这一情形**已经发生**，"
          "必须用 `wrap_axes`/`check_wrap` 判其是否正确；" % n_gh)
    print("     并且**长度读数可能已被绕盒污染**（框架守卫的原文警告：读数会超过 L）。")
else:
    print("\n  ⇒ 按框架口径**尚无场绕盒** ⇒ 该监控项暂未进入可判状态（待板条更长时复测）。")
