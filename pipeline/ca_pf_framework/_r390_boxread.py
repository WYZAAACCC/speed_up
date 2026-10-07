#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r390_boxread.py —— 把当前算例的盒子/分辨率/成本一次读清。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M = os.path.join(HERE, '_exp', '_bk_mb', 'dry_goodA_400', 'meta.json')
d = json.load(open(M, encoding='utf-8'))
N = int(d['N'])
dx = float(d['dx_nm']) * 1e-9
L = float(d['L'])
print('=' * 84)
print('当前算例（dry_goodA_400）的盒子与分辨率')
print('=' * 84)
print('  胞数 N            = %d  (= %d^3 = %s 胞)' % (N ** 3, N, format(N ** 3, ',')))
print('  格子 Δx           = %.3f nm' % (dx * 1e9))
print('  盒子棱长 L        = %.4f µm  ⇒ 体积 = %.1f µm³' % (L * 1e6, (L * 1e6) ** 3))
print('  体元 Δx³          = %.4e µm³' % ((dx * 1e6) ** 3))
print()
print('  ## 播种几何')
p = d.get('plate')
print('    plate（原始参数） = %s' % (p,))
for k in ('nv', 'gap_nm', 'laths', 'gen'):
    if k in d:
        print('    %-16s = %s' % (k, d[k]))
print()
print('  ## 时间/成本')
for k in ('dt', 't_sim', 'steps', 'Mob', 'DF', 'gamma0'):
    if k in d:
        print('    %-16s = %s' % (k, d[k]))
print()
print('  ## 分辨率判据核对（`BLOCK_SELFAC.md` §7.2c：`t/Δx ≳ 8`，含界面 `≳ 10`）')
print('    实测"在位的场"厚度 = 499 / 501 / 808 … 1035 nm（12 个场）')
for t in (499.0, 510.0, 808.0, 1035.0):
    print('      t = %6.0f nm ⇒ t/Δx = **%5.2f**' % (t, t / (dx * 1e9)))
print('    ⇒ 最薄的场 t/Δx = **%.2f**（判据 `≳8`：%s；更严的 `≳10`：%s）'
      % (499.0 / (dx * 1e9),
         '过' if 499.0 / (dx * 1e9) >= 8 else '不过',
         '过' if 499.0 / (dx * 1e9) >= 10 else '**不过**'))
