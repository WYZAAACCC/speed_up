#!/usr/bin/env python3
"""R51: 用**实测 RSS** 定内存标度（`4×phi` 的猜测是错的：实测 ~20×）。"""
import os
import subprocess

print('=== 实测 RSS（当前正在跑的臂，`ps` 采样）')
out = subprocess.run(['ps', '-eo', 'rss,args', '--no-headers'],
                     capture_output=True, text=True).stdout
seen = []
for line in out.splitlines():
    if '_bk_exp.py' not in line or 'grep' in line:
        continue
    parts = line.split(None, 1)
    if len(parts) != 2:
        continue
    rss = int(parts[0]) / 1024.0            # MB
    cmd = parts[1]
    N = nreg = '?'
    for i, t in enumerate(cmd.split()):
        if t == '--N':
            N = cmd.split()[i + 1]
        if t == '--laths':
            nreg = len(cmd.split()[i + 1].split(',')) + 1
    seen.append((N, nreg, rss))
    print('  N=%-4s nreg=%-4s RSS=%7.0f MB   (%.2f MB / (N³·nreg/1e6))'
          % (N, nreg, rss, rss / ((int(N) ** 3 * int(nreg)) / 1e6)))
if seen:
    k = sum(r / ((int(N) ** 3 * int(nreg)) / 1e6) for N, nreg, r in seen) / len(seen)
    print()
    print('=== 拟合: RSS ≈ %.2f MB × (N³·nreg/1e6)' % k)
    print('  %-10s %-8s %-10s %-12s %s' % ('盒(µm)', 'N@62.5', 'nreg', 'N³nreg/1e6', '预测 RSS'))
    for L in (6.0, 8.0, 10.0, 12.0):
        for nreg in (7, 12, 19):
            N = int(round(L * 1000 / 62.5))
            key = N ** 3 * nreg / 1e6
            print('  %-10.1f %-8d %-10d %-12.1f %.2f GB'
                  % (L, N, nreg, key, k * key / 1024))
