#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_mem_scaling.py —— **量构造期 RSS 随 `N` 的标度**（判 `N=128` 是否可行）。

## 为什么（`R635 §7` 的矛盾）
`hW1`（`N=128`）实测单进程 RSS **24 116 MB**，而 `L1`（`N=64`）只有 **620 MB**：
`24 116 / 620 = 38.9`，而 `(128/64)³ = 8` 只能解释 8 倍
⇒ **两者至少差 4.9 倍** ⇒ 必有一方不是"稳态 RSS"（例如构造峰值 vs 运行稳态）。

## 做法
分别构造 `N=48 / 64 / 96` 的 `LevelSetMulti`，记录**构造后** RSS；每档跑几次
`advance` 后再记一次。若 `RSS ∝ N³` ⇒ 可外推 `N=128`。
"""
import os
import sys

import numpy as np

sys.path.insert(0, "/mnt/f/speed_up/pipeline/ca_pf_framework")
import windowB_surface as W  # noqa: E402


def rss_mb():
    for ln in open('/proc/self/status'):
        if ln.startswith('VmRSS:'):
            return int(ln.split()[1]) / 1024.0
    return float('nan')


def vmhwm_mb():
    for ln in open('/proc/self/status'):
        if ln.startswith('VmHWM:'):
            return int(ln.split()[1]) / 1024.0
    return float('nan')


dx = 62.5e-9
print("=" * 84)
print("构造期 / 运行期 RSS 随 N 的标度（`nv=220`，与生产同）")
print("=" * 84)
print("  %-6s %-14s %-14s %-14s %-12s" % ('N', '构造后 RSS', 'VmHWM 峰值', 'N³/N₆₄³', 'RSS/构造'))
base = None
for N in (48, 64, 96):
    g = W.LevelSetMulti(N, N * dx, nv=220, gamma=0.25, Mob=1e-9,
                        df=[0.0, -1e7], reinit_every=20)
    r0, h0 = rss_mb(), vmhwm_mb()
    if base is None:
        base = r0
    print("  %-6d %-14.1f %-14.1f %-14.2f %s"
          % (N, r0, h0, (N / 48.0) ** 3, '基准' if base == r0 else '%.2f×' % (r0 / base)))
    del g
print()
print("  ⇒ 若 `RSS ∝ N³`：外推 **N=128** 的构造 RSS =")
r64 = None
for N in (64,):
    g = W.LevelSetMulti(N, N * dx, nv=220, gamma=0.25, Mob=1e-9,
                        df=[0.0, -1e7], reinit_every=20)
    r64 = rss_mb()
    del g
if r64:
    print("     由 N=64 的 %.1f MB × (128/64)³ = %.1f MB = **%.2f GB**"
          % (r64, r64 * 8, r64 * 8 / 1024.0))
print()
print("  ⇒ 若外推值 ≲ 8 GB ⇒ **N=128 可行**（先前 24 GB 应是别的原因，如多进程并存）")
