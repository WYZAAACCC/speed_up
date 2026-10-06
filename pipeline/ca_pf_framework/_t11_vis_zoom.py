#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_vis_zoom.py <tag> <field> [step ...] —— ★ 3D **缩放**视觉检查。

为什么要缩放：`c2B647` 的场只有几百胞，在 128³ 盒里是个小点（上一版看不出来）。
本版把坐标**平移到该场自己的包围盒**，并按**真实比例**显示三轴
⇒ 直接看出"是团、还是细长条"，以及"沿哪个方向长"。
"""
import glob
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
OUTD = "/mnt/f/speed_up/_vis"
DX = 62.5e-9
tag = sys.argv[1]
tag = tag[4:] if tag.startswith('dry_') else tag
field = int(sys.argv[2])
steps = [int(x) for x in sys.argv[3:]] or [100, 200]
os.makedirs(OUTD, exist_ok=True)

fig = plt.figure(figsize=(15, 5.2))
for i, st in enumerate(steps):
    p = os.path.join(ROOT, "dry_%s" % tag, "snap_%05d.npz" % st)
    if not os.path.exists(p):
        continue
    with np.load(p, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    idx = np.argwhere(reg == field)
    if idx.shape[0] < 8:
        continue
    lo = idx.min(0)
    idx = idx - lo                       # 平移到自己的原点
    ext = idx.max(0) + 1                 # 三轴跨度（胞）
    nm = ext * DX * 1e9
    ax = fig.add_subplot(1, len(steps), i + 1, projection='3d')
    ax.scatter(idx[:, 2], idx[:, 1], idx[:, 0], s=9, c='tab:blue',
               alpha=0.55, linewidths=0)
    ax.set_title('step=%d  field %d  (%d cells)\n'
                 'extent: %.0f x %.0f x %.0f nm\nratios  %.2f : %.2f : 1'
                 % (st, field, idx.shape[0], nm[0], nm[1], nm[2],
                    nm.max() / nm.min(), np.sort(nm)[1] / nm.min(),
                    ), fontsize=9)
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z')
    mx = int(ext.max())
    ax.set_xlim(0, mx); ax.set_ylim(0, mx); ax.set_zlim(0, mx)
    ax.set_box_aspect((ext[2], ext[1], ext[0]))   # ★ 真实比例
    ax.view_init(elev=18, azim=32)
    print("  step=%d  %d 胞  extent=%.0fx%.0fx%.0f nm  比例 %.2f:%.2f:1"
          % (st, idx.shape[0], nm[0], nm[1], nm[2],
             nm.max() / nm.min(), np.sort(nm)[1] / nm.min()))

out = os.path.join(OUTD, "zoom_%s_f%d.png" % (tag, field))
plt.tight_layout()
plt.savefig(out, dpi=110)
print("⇒ 已写出 %s" % out)
