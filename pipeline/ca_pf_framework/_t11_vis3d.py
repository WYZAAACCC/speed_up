#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vis3d.py <tag> <field> [step ...] —— ★ 3D 视觉检查（用户已允许）。

画法：对指定步，取该场的胞坐标 → 3D 散点（按体素大小着色）。
  · **主体**（最大连通分量）用**蓝色**；
  · **孤儿胞**（其余分量）用**红色、加大点** —— 直接看它们长在哪里。
输出 PNG 到 `F:\\speed_up\\_vis\\`（Windows 侧，可直接看）。
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402
from scipy import ndimage                # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
OUTD = "/mnt/f/speed_up/_vis"
DX = 62.5e-9
tag = sys.argv[1]
tag = tag[4:] if tag.startswith('dry_') else tag
field = int(sys.argv[2])
steps = [int(x) for x in sys.argv[3:]] or [100, 200, 300]
os.makedirs(OUTD, exist_ok=True)

fig = plt.figure(figsize=(16, 5.4))
n = len(steps)
for i, st in enumerate(steps):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        print("  缺 %s" % p)
        continue
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    m = (reg == field)
    if m.sum() < 8:
        continue
    lab, ncomp = ndimage.label(m, structure=np.ones((3, 3, 3)))
    szs = np.bincount(lab.ravel())
    szs[0] = 0
    bid = int(np.argmax(szs))
    main = (lab == bid)
    orph = m & ~main

    ax = fig.add_subplot(1, n, i + 1, projection='3d')
    # 主体（降采样以控内存）
    idx = np.argwhere(main)
    if idx.shape[0] > 60000:
        idx = idx[::max(1, idx.shape[0] // 60000)]
    ax.scatter(idx[:, 2], idx[:, 1], idx[:, 0], s=1.2, c='tab:blue',
               alpha=0.30, linewidths=0, label='main body (%d cells, %.1f%%)'
               % (szs[bid], 100.0 * szs[bid] / m.sum()))
    oi = np.argwhere(orph)
    if oi.shape[0]:
        ax.scatter(oi[:, 2], oi[:, 1], oi[:, 0], s=14, c='red',
                   marker='o', alpha=0.95, linewidths=0,
                   label='orphans (%d)' % oi.shape[0])
    ax.set_title('step=%d  field %d\n%d comps, main = %.1f%%'
                 % (st, field, ncomp, 100.0 * szs[bid] / m.sum()), fontsize=10)
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z')
    ax.legend(fontsize=7, loc='upper left')
    ax.view_init(elev=22, azim=35)
    # 等比例显示
    mx = max(reg.shape)
    ax.set_xlim(0, mx); ax.set_ylim(0, mx); ax.set_zlim(0, mx)
    ax.set_box_aspect((1, 1, 1))
    print("  step=%d 主体 %d 胞 / 孤儿 %d 胞 / 分量 %d"
          % (st, szs[bid], int(orph.sum()), ncomp))

out = os.path.join(OUTD, "vis_%s_f%d.png" % (tag, field))
plt.tight_layout()
plt.savefig(out, dpi=105)
print("⇒ 已写出 %s" % out)
