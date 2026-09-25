#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fig_boxB_sections.py --- 盒子 B 完整轨迹的**剖面展示**：不同组织不同颜色。

读 results_boxB_N080_dx250nm_{final.npz,traj.csv,summary.json}：
  (a)(b)(c) 三个正交中面剖面（z/y/x 中面），按变体 ID 着色（母相浅灰）
  (d) 轨迹：f 与板片厚 vs 步数
"""
import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for _f in ('/mnt/c/Windows/Fonts/simhei.ttf', '/mnt/c/Windows/Fonts/msyh.ttc'):
    try:
        fm.fontManager.addfont(_f)
    except Exception:
        pass
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

TAG = 'boxB_N080_dx250nm'
d = np.load('results_%s_final.npz' % TAG)
reg, N, dx = d['reg'], int(d['N']), float(d['dx'])
L = N * dx
S = json.load(open('results_%s_summary.json' % TAG))
rows = np.genfromtxt('results_%s_traj.csv' % TAG, delimiter=',', names=True)
print('f=%.4f  t_plate=%.3f um  steps=%d  stop=%s' % (d['f'], d['t_plate'], S['steps'], S['stop']))

# ★ 记账： 是**暗/亮成对**的（0/1 是同一色的深浅）⇒ 按顺序取 12 个会出现
#   "浅蓝/浅橙/浅绿"等与母相浅灰易混的颜色（我第一版就误判了）。
#   这里取 12 个**高区分度暗色**：tab10（10 个）+ Dark2 的两个。
import matplotlib.cm as _cm
cols = [plt.get_cmap('tab10')(i / 10.0) for i in range(10)]
cols.append(_cm.Dark2(0.05))
cols.append(_cm.Dark2(0.62))
ext = [0, L * 1e6, 0, L * 1e6]
fig = plt.figure(figsize=(15.5, 11.5))
for j, (name, sl) in enumerate((('z 中面 (z=%.1f um)' % (L * 5e5), reg[:, :, N // 2]),
                                ('y 中面', reg[:, N // 2, :]),
                                ('x 中面', reg[N // 2, :, :]))):
    ax = fig.add_subplot(2, 2, j + 1)
    img = np.zeros(sl.shape + (3,))
    img[:] = np.array([1.0, 1.0, 1.0])   # 母相纯白
    for v in range(1, 13):
        img[sl == v] = cols[v - 1][:3]
    ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=ext)
    ax.set_title('%s —— 按变体着色（母相浅灰）' % name, fontsize=10)
    ax.set_xlabel('um'); ax.set_ylabel('um')
    if j == 0:
        vv = np.bincount(reg.ravel(), minlength=13)[1:] / float((reg != 0).sum())
        ax.plot([], [], color=(1, 1, 1), lw=6, label='母相(白)')
        for v in range(12):
            ax.plot([], [], color=cols[v], lw=6,
                    label='V%d  %.1f%%' % (v + 1, 100 * vv[v]))
        ax.legend(fontsize=5.2, ncol=3, loc='upper right', framealpha=0.8)
ax = fig.add_subplot(2, 2, 4)
ax.plot(rows['step'], rows['f'], '-', color='tab:blue', label='转变分数 f')
ax.set_xlabel('step'); ax.set_ylabel('f', color='tab:blue')
ax2 = ax.twinx()
ax2.plot(rows['step'], rows['t_plate'] * 1e6, '-', color='tab:red', label='板片厚')
ax2.set_ylabel('t = 2f/S_v (um)', color='tab:red')
ax.set_title('轨迹：f 与板片厚  (steps=%d, %.2f s/步, 墙钟 %.0f min, stop=%s)'
             % (S['steps'], S['s_per_step'], S['wall'] / 60, S['stop']), fontsize=10)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('FIG_boxB_sections_%s.png' % TAG, dpi=165)
print('saved FIG_boxB_sections_%s.png' % TAG)
