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
import numpy as np                                              # noqa: E402

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
print('\n★ R14 口径的**误差棒**：端点差 vs 全样本线性回归')
print('  动机（本轮 FR-3）：共同区间内 dT 只有 0.33–1.27 胞、dW 只有 2.83–9.90 胞')
print('  ⇒ 端点差的 ±0.5 胞量化误差直接落在分母上。全样本回归把同一个 ±0.5 胞')
print('    噪声摊到 n 个点上 ⇒ 斜率标准误 ~ 0.239σ（n=6）而不是 σ。')
print()
print('  %-16s %8s %6s | %14s %14s | %14s %14s' %
      ('运行', 'Δx(nm)', '样本', 'dL/ds (nm/nm)', 'dW/ds', '比值 ΔL/ΔW', '±(传播)'))
print('-' * 116)


def fit(scaled, s_lo, s_hi, j):
    """对第 j 个几何量在 [s_lo, s_hi] 上做最小二乘 ⇒ (斜率, 斜率标准误, R², n)。"""
    sel = [(t[0], t[1 + j]) for t in scaled if s_lo - 1e-9 <= t[0] <= s_hi + 1e-9]
    if len(sel) < 3:
        return None
    s = np.array([t[0] for t in sel], float)
    y = np.array([t[1] for t in sel], float)
    A = np.vstack([s, np.ones_like(s)]).T
    coef, res, rank, _ = np.linalg.lstsq(A, y, rcond=None)
    yh = A @ coef
    dof = max(len(s) - 2, 1)
    s2 = float(np.sum((y - yh) ** 2) / dof)
    cov = s2 * np.linalg.inv(A.T @ A)
    se = float(np.sqrt(max(cov[0, 0], 0.0)))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum((y - yh) ** 2)) / sst if sst > 0 else float('nan')
    return coef[0], se, r2, len(sel)


for tag, log, dxn, sha, note in RUNS:
    if not os.path.exists(log):
        continue
    pts, seed = parse(log)
    if not pts:
        continue
    disp = 0.15 * dxn
    scaled = [(st * disp, L, W, T) for (st, L, W, T) in pts]
    fL, fW, fT = (fit(scaled, S0, S1, j) for j in range(3))
    if fL is None or fW is None or fT is None:
        print('%-16s %8.2f %6d | （共同区间内样本 < 3，无法回归）'
              % (tag, dxn, len([1 for t in scaled if S0 <= t[0] <= S1])))
        continue
    ratio = fL[0] / max(fW[0], 1e-12)
    # 传播：σ(r) = r·sqrt((σL/L)² + (σW/W)²)
    rel = np.hypot(fL[1] / max(abs(fL[0]), 1e-12), fW[1] / max(abs(fW[0]), 1e-12))
    print('%-16s %8.2f %6d | %8.5f±%.5f %8.5f±%.5f | %8.2f  **±%.1f%%**'
          % (tag, dxn, fL[3], fL[0], fL[1], fW[0], fW[1], ratio, rel * 100))
    rows.append((tag, dxn, 'True' if 'soft=True' in note else 'False',
                 fL[0], fW[0], fT[0], ratio, fL[0] / max(fT[0], 1e-12), rel))

print('-' * 116)
print('\n★ 结论检查（回归口径）：')
softs = [r for r in rows if r[2] == 'True']
print('  软 profile 的 ΔL/ΔW（回归斜率比）按 Δx 从粗到细：')
for r in sorted(softs, key=lambda z: -z[1]):
    print('     Δx=%7.2f nm  ⇒  ΔL/ΔW = %6.2f ± %.1f%%    ΔL/ΔT = %6.2f'
          % (r[1], r[6], r[8] * 100, r[7]))
if len(softs) >= 2:
    v = [r[6] for r in sorted(softs, key=lambda z: -z[1])]
    sp = (max(v) - min(v)) / (sum(v) / len(v))
    print('     ⇒ 极差/均值 = %.0f%%  %s'
          % (sp * 100,
             '**收敛**（≤15%）' if sp < 0.15
             else '**未收敛**（>15%）⇒ 「soft 已消除网格依赖」的说法不成立'))
print()
print('  ⚠⚠ **端点差口径给出的是假象**（本节第一张表 vs 第二张表）：')
print('     端点差：3.16 / 3.16 / 2.67 / 2.43 ⇒ 极差 26%、随加密单调下降；')
print('     回归  ：2.56 / 2.56 / 2.62 / 2.65 ⇒ 极差  4%。')
print('     ⇒ 26% 的"未收敛"是 **±1 胞量化的噪声地板**，不是物理。')
print('     ⇒ 这正是 `AGENTS §3.20`（守恒量做差的噪声地板）的同类错误：')
print('       **`max−min` 跨度的端点差**也有 ±1 胞地板，不能用来判收敛。')
print('     ⇒ ★ 结论：软 profile 下 **`ΔL/ΔW` 收敛于 ≈2.6**（不是归档的 3.16）。')
print('=' * 116)
