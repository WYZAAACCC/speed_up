#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_analyze_dx.py --- ★ 把 Δx 收敛扫描的**共同物理区间**读数**机器化**，不再手算

为什么要做（Round 141，用户指示「重新检查…最终结果，不要误用数据」）
------------------------------------------------------------------
`R14` 规定：`ΔL:ΔW:ΔT` 必须在**共同物理区间**上比。
物理时间由 `dt = 0.15·Δx/(M0·Δf)` 定 ⇒ **每步的标称位移 = 0.15·Δx**（纯 CFL）
⇒ 换个 Δx，"同一步数"就是**不同的物理时间**。跨网格比较必须换算。

本脚本从各日志里**正则提取** `(step, L, W, T)`，按 `s = step·0.15·Δx_nm` 换算标称位移，
在 **共同区间 [1250, 3750] nm**（`R14`）上**线性插值**端点，再算 `ΔL/ΔW`、`ΔL/ΔT`。
⇒ 从此不再有"手算映射错区间"的空间。

用法：python3 _analyze_dx.py
"""
import os
import re
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# (标签, 日志, Δx_nm, 引擎 SHA, 备注)
RUNS = [
    ('DX1  硬 profile', '_w2_dx1.log', 166.70, 'b9565f69', 'N=64 10.67µm soft=False'),
    ('DX2  硬 profile', '_w2_dx2.log', 83.35, 'b9565f69', 'N=128 10.67µm soft=False'),
    ('ED3  软 profile', '_w2_edsoft3.log', 166.70, 'b9565f69', 'N=64 10.67µm soft=True'),
    ('DX2S 软 profile', '_w2_dx2soft.log', 83.35, 'b9565f69', 'N=128 10.67µm soft=True'),
    ('DXF1 软/4µm盒', '_w2_dxf1.log', 83.35, 'b9565f69', 'N=48 4.0µm soft=True'),
    ('DXF2 软/4µm盒', '_w2_dxf2.log', 50.00, 'b9565f69', 'N=80 4.0µm soft=True'),
    ('DXF3 软/4µm盒', '_w2_dxf3.log', 33.34, 'b9565f69', 'N=120 4.0µm soft=True'),
]
S0, S1 = 1250.0, 3750.0                     # R14 共同物理区间（nm）
RE_GEO = re.compile(r'L=([-\d.]+)\s+W=([-\d.]+)\s+T=([-\d.]+)\s+nm')
RE_STEP = re.compile(r'\[step\s+(\d+)\]')


def parse(path):
    pts, seed = [], None
    with open(path, 'r', errors='replace') as f:
        for ln in f:
            m = RE_STEP.search(ln)
            if m:
                g = RE_GEO.search(ln)
                if g:
                    pts.append((int(m.group(1)), float(g.group(1)),
                                float(g.group(2)), float(g.group(3))))
            elif '种子实测' in ln:
                g = RE_GEO.search(ln)
                if g:
                    seed = (float(g.group(1)), float(g.group(2)), float(g.group(3)))
    return pts, seed


def interp(pts, s_target):
    """在标称位移 s = step·0.15·Δx 上线性插值 ⇒ 返回 (L,W,T) 或 None。"""
    for i in range(len(pts) - 1):
        s0, s1 = pts[i][0], pts[i + 1][0]
        if s0 <= s_target <= s1:
            w = (s_target - s0) / max(s1 - s0, 1e-12)
            return tuple(pts[i][j + 1] + w * (pts[i + 1][j + 1] - pts[i][j + 1])
                         for j in range(3))
    return None


print('=' * 116)
print('_analyze_dx —— 共同物理区间 [%d, %d] nm（标称位移 = step·0.15·Δx）上的 ΔL:ΔW:ΔT'
      % (S0, S1))
print('=' * 116)
hdr = ('%-16s %8s %6s %-9s %10s %10s %10s | %8s %8s | %8s %8s'
       % ('运行', 'Δx(nm)', '盒(µm)', 'profile', 'L(nm)', 'W(nm)', 'T(nm)',
          'ΔL/ΔW', 'ΔL/ΔT', 'fill_n', '胞数'))
print(hdr)
print('-' * 116)
rows = []
for tag, log, dxn, sha, note in RUNS:
    if not os.path.exists(log):
        print('%-16s  （缺 %s）' % (tag, log))
        continue
    pts, seed = parse(log)
    if not pts:
        print('%-16s  （无读数）' % tag)
        continue
    disp = 0.15 * dxn
    scaled = [(st * disp, L, W, T) for (st, L, W, T) in pts]
    a = interp(scaled, S0)
    b = interp(scaled, S1)
    if a is None or b is None:
        print('%-16s  （区间未覆盖：s 范围 %.0f–%.0f nm）'
              % (tag, scaled[0][0], scaled[-1][0]))
        continue
    dL, dW, dT = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    soft = 'soft=True' if 'soft=True' in note else 'soft=False'
    m = re.search(r'(\d\.\d+)µm', note)
    print('%-16s %8.2f %6s %-9s %10.1f %10.1f %10.1f | %8.2f %8.2f'
          % (tag, dxn, (m.group(1) if m else '?'), soft, b[0], b[1], b[2],
             dL / max(dW, 1e-9), dL / max(dT, 1e-9)))
    print('%-16s %8s %6s %-9s %10.1f %10.1f %10.1f | %6.2f胞 %6.2f胞 %6.2f胞'
          % ('   └ 区间增量', '', '', '', dL, dW, dT,
             dL / dxn, dW / dxn, dT / dxn))
    rows.append((tag, dxn, soft, dL, dW, dT, dL / max(dW, 1e-9), dL / max(dT, 1e-9)))

print('-' * 116)
print('\n★ 结论检查：')
softs = [r for r in rows if 'True' in r[2]]
hards = [r for r in rows if 'False' in r[2]]
print('  软 profile（F-2 修完、`elastic_soft=True`）的 ΔL/ΔW，按 Δx 从粗到细：')
for r in sorted(softs, key=lambda z: -z[1]):
    print('     Δx=%7.2f nm  ⇒  ΔL/ΔW = %6.2f   ΔL/ΔT = %6.2f' % (r[1], r[6], r[7]))
if len(softs) >= 2:
    v = [r[6] for r in sorted(softs, key=lambda z: -z[1])]
    print('     ⇒ 极差/均值 = %.0f%%  %s'
          % ((max(v) - min(v)) / (sum(v) / len(v)) * 100,
             '**收敛**（≤15%）' if (max(v) - min(v)) / (sum(v) / len(v)) < 0.15
             else '**未收敛**（>15%）⇒ 既有"soft 已消除网格依赖"的说法不成立'))
print('=' * 116)
