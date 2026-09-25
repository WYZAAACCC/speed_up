#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_t21b7.py --- T2.1b-7：**符号约定判决**（W-5'）。

本判据回答一个此前从未被验过的问题：LevelSetMulti/PF3D 里 Filesystem      1K-blocks       Used Available Use% Mounted on
none             12303688          0  12303688   0% /usr/lib/modules/6.18.33.2-microsoft-standard-WSL2
none             12303688          4  12303684   1% /mnt/wsl
drivers         377079328  375727052   1352276 100% /usr/lib/wsl/drivers
/dev/sdd       1055762868   42653492 959405904   5% /
none             12303688         40  12303648   1% /mnt/wslg
none             12303688          0  12303688   0% /usr/lib/wsl/lib
rootfs           12297932       2772  12295160   1% /init
none             12303688        592  12303096   1% /run
none             12303688          0  12303688   0% /run/lock
none             12303688          0  12303688   0% /run/shm
none             12303688         80  12303608   1% /mnt/wslg/versions.txt
none             12303688         80  12303608   1% /mnt/wslg/doc
C:\             377079328  375727052   1352276 100% /mnt/c
D:\             620793304  591237288  29556016  96% /mnt/d
E:\             976754688  913881088  62873600  94% /mnt/e
F:\            1953479676 1239812884 713666792  64% /mnt/f
none                 1024          0      1024   0% /run/credentials/systemd-journald.service
tmpfs            12303692          4  12303688   1% /tmp
none                 1024          0      1024   0% /run/credentials/systemd-resolved.service
none                 1024          0      1024   0% /run/credentials/getty@tty1.service
tmpfs             2460736         12   2460724   1% /run/user/0（每区域驱动力）
的正负各代表什么？此前所有调用（M2 驱动、文档）都用  却称之为"转变驱动"。

验证方法：同一 slab 初值、无弹性（C=None）、γ=0，**同时测方向与幅度**：
  ① 区域 1 的体积变化 dV1（>0 = 长大）
  ② 有符号界面位移 /(M|df|)（应 = ±1）
判据（正/负两个方向都要给对）：
  (a) df[variant] > 0  => dV1 > 0 且 v/(M df) = +1
  (b) df[variant] < 0  => dV1 < 0 且 v/(M df) = +1（= 缩小，幅度仍对）
  并与 PF3D 的约定交叉核对：（梯度下降）也要求 dG > 0 = 变体有利。
"""
import numpy as np

from windowB_surface import LevelSetMulti

ok = {}


def rec(tag, good, extra=''):
    ok[tag] = bool(good)
    print('   %-58s %s %s' % (tag, 'PASS' if good else 'FAIL', extra))


def one(sign, mag=1e8, nv=1, N=48, dx=2e-9, M=1e-9, nstep=40, a_frac=0.25):
    dfs = [0.0] * (nv + 1)
    dfs[1] = sign * mag
    g = LevelSetMulti(N, N * dx, nv=nv, gamma=0.0, Mob=M, df=dfs,
                      reinit_every=0)
    z = (np.arange(N)[None, None, :] + 0.5) * dx
    L = N * dx
    a = a_frac * L
    g.phi[1] = np.where(z <= a, -np.minimum(z, a - z),
                        np.minimum(z - a, L - z)) * np.ones((N, N, N))
    g.near0 = a
    g.init_parent()
    V0 = int((g.region() == 1).sum())
    _, z0 = g.iface_offset(1, 0, 2, near=g.near0)
    dt = 0.1 * dx / (M * mag)
    for _ in range(nstep):
        g.advance(dt, extend='edt', band_cells=20)
    V1 = int((g.region() == 1).sum())
    _, z1 = g.iface_offset(1, 0, 2, near=g.near0)
    return V0, V1, (z1 - z0) / (nstep * dt) / (M * mag)


print('---- T2.1b-7 符号约定判决（N=48 dx=2nm nstep=40；C=None γ=0；nv=1）----')
print('   df[variant]   V0      V1      dV1      v/(M|df|)   读法')
rows = {}
for sgn, lab in ((+1.0, '+1e8'), (-1.0, '-1e8')):
    V0, V1, vr = one(sgn)
    rows[sgn] = (V1 - V0, vr)
    print('   %-12s  %6d  %6d  %+7d   %+9.4f    %s'
          % (lab, V0, V1, V1 - V0, vr, '长大' if V1 - V0 > 0 else '缩小'))
rec('T2.1b-7a df[variant] > 0 => 长大（变体有利）', rows[+1.0][0] > 0,
    'dV1=%+d' % rows[+1.0][0])
rec('T2.1b-7b df[variant] < 0 => 缩小（变体不利）', rows[-1.0][0] < 0,
    'dV1=%+d' % rows[-1.0][0])
rec('T2.1b-7c 两个方向 |v|/(M|df|) 都 = 1（幅度正确，< 2%）',
    abs(abs(rows[+1.0][1]) - 1.0) < 0.02 and abs(abs(rows[-1.0][1]) - 1.0) < 0.02,
    'v+ = %+.4f ; v- = %+.4f' % (rows[+1.0][1], rows[-1.0][1]))
rec('T2.1b-7d 约定的指向：df > 0 = 变体有利（= PF3D 的 ∂f/∂φ_v = -dG 梯度下降）',
    rows[+1.0][0] > 0 and rows[-1.0][0] < 0)
print()
print('   ⇒ 结论：**df > 0 = 变体有利**。此前 M2 驱动传 df = -1e8，')
print('     即一直在**溶解**晶核；M2 报的"转变分数"是弹性自协调撑起来的（见审计 §11）。')
print()
print('T2.1b-7 汇总: %s' % ('ALL PASS' if all(ok.values())
                           else '%d/%d PASS' % (sum(ok.values()), len(ok))))
if not all(ok.values()):
    print('FAIL 项: %s' % [k for k, v in ok.items() if not v])
