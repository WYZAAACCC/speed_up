#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r317_pickvar.py —— 为"**只换变体集**"的单变量实验挑合适的变体对（先算 `‖Δε‖`）。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from T16_verify_rve import EPS0  # noqa: E402


def main():
    print('=' * 96)
    print('_r317 —— 各变体对的 `‖ε⁰_v − ε⁰_w‖_F`（为单变量实验挑对）')
    print('=' * 96)
    E = {v: np.asarray(EPS0[v - 1], float) for v in range(1, len(EPS0) + 1)}
    # 以变体 1 为基准（因为 `1,1,1,x,x,x` 的两块之一恒为 V1）
    rows = []
    for w in range(2, len(EPS0) + 1):
        d = float(np.linalg.norm(E[1] - E[w]))
        rows.append((w, d))
    print('  ## 与 **V1** 的失配 `‖ε⁰_1 − ε⁰_w‖_F`')
    print('     %-6s %s' % ('w', '‖Δε‖'))
    for (w, d) in sorted(rows, key=lambda x: x[1]):
        print('     V%-5d %.6f' % (w, d))
    lo = min(rows, key=lambda x: x[1])
    hi = max(rows, key=lambda x: x[1])
    print()
    print('  ⇒ **最小** = V%d（%.6f）；**最大** = V%d（%.6f）⇒ 相差 **%.2f 倍**'
          % (lo[0], lo[1], hi[0], hi[1], hi[1] / lo[1]))
    print()
    print('  ## 建议的单变量实验（同几何 / 同 N / 同 plate / 同块布局，**只换变体**）')
    print('     基准（已有）：`--laths 1,1,1,3,3,3`（V1 与 V3）')
    print('     ⇒ ‖Δε(V1,V3)‖ = %.6f' % dict(rows)[3])
    print('     **对照 A（近）**：`--laths 1,1,1,%d,%d,%d` ⇒ ‖Δε‖ = %.6f（%.2f× 基准）'
          % (lo[0], lo[0], lo[0], lo[1], lo[1] / dict(rows)[3]))
    print('     **对照 B（远）**：`--laths 1,1,1,%d,%d,%d` ⇒ ‖Δε‖ = %.6f（%.2f× 基准）'
          % (hi[0], hi[0], hi[0], hi[1], hi[1] / dict(rows)[3]))
    print()
    print('  ⇒ **预言**：若 σ 响应变体配置，则 `ed` 离散度应随 ‖Δε‖ **单调增**。')
    print('     ⚠ 若三臂的 `ed` 离散度**都与 ‖Δε‖ 无关** ⇒ σ **不**由变体配置主导。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
