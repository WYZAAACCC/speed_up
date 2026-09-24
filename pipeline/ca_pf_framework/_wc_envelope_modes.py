#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_wc_envelope_modes.py --- 用 wc_cet 的多晶基准算例，比较三种捕获模式的取向淘汰"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0]]
import ca3d
from ca3d import quat_to_axes
import verify_ca3d_wc_cet as W

n = W.nhat_tilt(35.0)
print("倾斜梯度 n̂ = (%.3f, %.3f, %.3f); 基准算例: N=150, 3x3 种子, 间距 25, nst=240" % tuple(n))
print("  模式        存活/总数   占前沿(on_lead)的晶粒(-对齐度)      前沿持有者数")
for cap in ("envelope", "analytic", "decentered"):
    r = W._wc_case(nst=240, N=150, n_t=3, n_y=3, spacing=25, seed=99, capture=cap)
    ca = r["ca"]; gids = r["gids"]
    def align(g):
        P = ca.axes[g]
        # 该取向的 <100> 轴与 n̂ 的最大夹角余弦 = 取向对齐度
        return max(abs(float(P[:, a] @ n)) for a in range(3))
    on = r["onlead"]
    al_on = sorted([(round(align(g), 3), int(g)) for g in on], reverse=True)
    print("  %-11s %2d/%-2d      %-45s %d" % (
        cap, len(r["alive"]), len(gids),
        " ".join("g%d(%.2f)" % (g, a) for a, g in al_on), len(on)))
    # 全体的对齐度分布 vs 在前沿者
    allal = sorted([align(g) for g in gids], reverse=True)
    print("              全体对齐度(降序): %s" % " ".join("%.2f" % x for x in allal))