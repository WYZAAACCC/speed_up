#!/usr/bin/env python3
"""R51: **算例成本标度律**（用已有臂的实测 `wall_s` 反推，用于盒子设计）。

目的（用户**条件 4**："在本机内存容许并且在可接受的计算用时之内"）：
  §33 定了分辨率下限 **Δx ≤ 63 nm**；现在要定**盒子能多大 / 能跑多少步**。
做法：从 `series.csv` 的 `wall_s` 取**每步墙钟**（用相邻行的差，避开累计），
      对 `N³ × nreg` 作拟合 —— 引擎是逐胞 stencil + 逐场 argmin，应大致线性于
      `nreg × N³`（多核后还会有饱和）。
⚠ 必须在**同一时刻的负载**下比较（本机常年 3–5 条臂并行）⇒ 结论带一个**并行折扣**，
  只用于**量级预算**，不当作单机峰值性能。
"""
import csv
import glob
import json
import math
import os

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')

CAND = [
    ('_exp/_bk_mb/dry_r49cad', 32, 3),
    ('_exp/_bk_mb/dry_r49vb', 48, 3),
    ('_exp/_bk_mb/dry_r49dg', 48, 3),
    ('_exp/_bk_mb/dry_r49vb', 48, 3),
    ('_exp/_bk_mb/dry_mb1s62', 96, 4),
    ('_exp/_bk_mb/dry_mb1s', 96, 4),
    ('_exp/_bk_eng/dry_r30reg', 96, 7),
    ('_exp/_bk_mb/dry_mb1L', 96, 7),
    ('_exp/_bk_closed/dry_cln11', 96, 12),
    ('_exp/_bk_eng/eng_eng12', 96, 7),
]
print('  %-26s %-5s %-6s %-12s %-12s %s'
      % ('臂', 'N', 'nreg', 'N³·nreg/1e6', '中位 秒/步', '来源'))
pts = []
for d, N, nreg in CAND:
    p = os.path.join(d, 'series.csv')
    if not os.path.exists(p):
        continue
    rows = list(csv.DictReader(open(p)))
    ws, xs = [], []
    for a, b in zip(rows, rows[1:]):
        try:
            dw = float(b['wall_s']) - float(a['wall_s'])
            dx = int(b['step']) - int(a['step'])
        except (KeyError, ValueError):
            continue
        if dx > 0 and dw > 0:
            ws.append(dw / dx)
            xs.append(int(a['step']))
    if len(ws) < 3:
        continue
    ws.sort()
    med = ws[len(ws) // 2]
    # 取后半段（含形核/长柱更接近稳态）
    half = ws[len(ws) // 2:]
    med2 = half[len(half) // 2]
    key = N ** 3 * nreg / 1e6
    pts.append((key, med2, N, nreg, d))
    print('  %-26s %-5d %-6d %-12.1f %-12.2f %s'
          % (os.path.basename(d), N, nreg, key, med2, 'series.csv'))

print()
if len(pts) >= 2:
    # 线性拟合 through origin: t = k * N³·nreg
    num = sum(k * t for k, t, *_ in pts)
    den = sum(k * k for k, t, *_ in pts)
    kfit = num / den
    print('=== 拟合（过原点）: 秒/步 ≈ %.3e × (N³·nreg)' % kfit)
    print('  %-26s %-12s %-12s %s' % ('臂', '实测', '拟合', '比'))
    for key, t, N, nreg, d in pts:
        print('  %-26s %-12.2f %-12.2f %.2f'
              % (os.path.basename(d), t, kfit * key, t / (kfit * key)))
    print()
    print('=== 设计盒子预算（用该标度律，**含当前并行折扣**）')
    print('  %-8s %-7s %-8s %-12s %-14s %s'
          % ('盒 (µm)', 'N@62.5', 'nreg', 'N³·nreg/1e6', '预测 秒/步', '600 步 = 小时'))
    for L_um, nreg in ((6.0, 7), (6.0, 12), (8.0, 7), (8.0, 12), (10.0, 12), (12.0, 12)):
        N = int(round(L_um * 1000 / 62.5))
        key = N ** 3 * nreg / 1e6
        t = kfit * key
        print('  %-8.1f %-7d %-8d %-12.1f %-14.2f %.1f'
              % (L_um, N, nreg, key, t, t * 600 / 3600))
    print()
    print('=== 内存粗算（phi 为 (nreg,N,N,N) float64 + 数份临时）')
    print('  单份 phi 字节 = 8·nreg·N³；峰值经验取 4×该值')
    for L_um, nreg in ((6.0, 7), (8.0, 12), (10.0, 12)):
        N = int(round(L_um * 1000 / 62.5))
        b = 8 * nreg * N ** 3
        print('  盒 %.0f µm N=%d nreg=%d : phi=%.2f GB  峰值≈%.2f GB'
              % (L_um, N, nreg, b / 1e9, 4 * b / 1e9))
