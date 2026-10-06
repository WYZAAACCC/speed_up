#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_wulff_audit.py —— **审计引擎的凸化实现**：它到底给出多大的 `h(a)/h(w)`？

## 为什么要查
`R30_AUDIT_LEDGER.md:2725-2740`（**2D 解析+几何**）预言：
  · 只凸化（`dip=0`）⇒ `h(0°)/h(90°) = **3.45**`
  · 凸化 + 45°凹陷 `c=4` ⇒ **`8.98`** ✅（这就是 `--mob-dip` 的设计依据）
而 **3D 引擎实测**（`R631`）：
  · `mob_wulff=1`（dip=0）⇒ `v_a/v_w = **1.30**`
  · `mob_wulff=1, dip=4` ⇒ **1.07**  ← ⚠ **方向相反**
⇒ **必须查清引擎实现是否兑现了它自己的解析预言**（用户指示：结果不符先怀疑实现错误）。

## 怎么做（纯计算，不跑算例）
调 `windowB_wulff.fast_support_factory(nh, av, wv, beta_h, beta_w, dip_c)`
拿到凸包顶点 `Vc`，再算支撑函数 `h(n) = max_j (Vc_j · n)`：
  · **`h(0°)` 与 `h(90°)` 的比值** = 引擎应当实现的 `v_a/v_w`
  · 与 2D 预言的 **3.45**（dip=0）/**8.98**（dip=4）比
"""
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_wulff as WL  # noqa: E402


def support_ratio(beta_h, beta_w, dip_c, nh, av, wv):
    _vf, Vc, _ = WL.fast_support_factory(nh, av, wv, beta_h=beta_h,
                                         beta_w=beta_w, dip_c=dip_c)
    V = np.asarray(Vc, float)
    if V.size == 0:
        return None, 0

    def h(n):
        n = np.asarray(n, float)
        n = n / np.linalg.norm(n)
        return float(np.max(V @ n))

    return h(av) / max(h(wv), 1e-300), V.shape[0]


print("=" * 96)
print("引擎凸化实现审计：`h(a)/h(w)`（= 引擎应实现的 `v_a/v_w`）")
print("=" * 96)
# 与生产一致的轴：n* 沿 z，a 沿 x，w 沿 y
nh = np.array([0.0, 0.0, 1.0])
av = np.array([1.0, 0.0, 0.0])
wv = np.array([0.0, 1.0, 0.0])
print("  %-10s %-10s %-14s %-12s %s"
      % ('beta_h', 'dip_c', 'h(a)/h(w)', '凸包顶点数', '2D 预言'))
for bh in (6.477,):
    for dip in (0.0, 1.0, 2.0, 4.0):
        r, nv = support_ratio(bh, 0.0, dip, nh, av, wv)
        pred = {0.0: '3.45', 1.0: '5.64', 2.0: '7.29', 4.0: '8.98'}.get(dip, '—')
        print("  %-10.3f %-10.1f %-14s %-12d %s"
              % (bh, dip, ('%.3f' % r) if r else 'None', nv, pred))
print()
# 也查 beta_w（第二钉扎轴）的影响
print("  --- 附：`beta_w` 的影响（dip=0）---")
for bw in (0.0, 2.3, 10.0):
    r, nv = support_ratio(6.477, bw, 0.0, nh, av, wv)
    print("  beta_w=%-6.2f  h(a)/h(w) = %s  (顶点 %d)"
          % (bw, ('%.3f' % r) if r else 'None', nv))
