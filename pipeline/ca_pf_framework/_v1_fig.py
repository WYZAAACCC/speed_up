#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_v1_fig.py --- 验证图: (a) 各向异性律散点 (b) 竞争/淘汰过程 + 对齐度-推进量相关'''
import os, json, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = '/mnt/c/Windows/Fonts/simhei.ttf'
if os.path.exists(FONT):
    from matplotlib import font_manager as fm
    fm.fontManager.addfont(FONT); plt.rcParams['font.family'] = fm.FontProperties(fname=FONT).get_name()
plt.rcParams['axes.unicode_minus'] = False

pts = []
for f in glob.glob(os.path.join(HERE, '_v1_out', 't3_aniso_law__*.json')):
    pts += json.load(open(f))['rows']
pts = np.array(pts)          # [r/ℓ, 1/Σ, ℓ/dx]
fig, axes = plt.subplots(1, 2, figsize=(15, 6.2))
ax = axes[0]
ax.plot([0.55, 1.02], [0.55, 1.02], 'k--', lw=1, label='解析律  r/ℓ = 1/Σ')
sc = ax.scatter(pts[:, 1], pts[:, 0], c=pts[:, 2], s=22, cmap='viridis', zorder=3)
plt.colorbar(sc, ax=ax, label='ℓ/dx (胞)')
ax.set_xlabel('1/Σ_a|p_a·n̂|   (解析预测)'); ax.set_ylabel('实测 r/ℓ')
ax.set_title('(a) 包络各向异性律：%d 个 (取向×方向) 测点\n平均偏离 %.2f 胞, 最大 %.2f 胞' % (
    len(pts), np.mean(np.abs(pts[:,0]-pts[:,1])*pts[:,2]), np.max(np.abs(pts[:,0]-pts[:,1])*pts[:,2])))
ax.legend(loc='upper left'); ax.grid(alpha=.3)

# (b) 淘汰过程
rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(HERE, '_v1_out', 't6b_lead__*.json')))]
gs = sorted(int(k) for k in rows[0]['align'])
cmap = plt.get_cmap('coolwarm')
allal, alllead = [], []
ax = axes[1]
for r in rows:
    for g in gs:
        al = r['align'][str(g)]
        ld = [ [x for x in rec if int(x[0]) == g][0][3] for st, lead, rec in r['hist'] ]
        st = [s for s, lead, rec in r['hist']]
        ax.plot(st, ld, color=cmap((al - 0.65) / 0.35), lw=1.6, alpha=.85)
        allal.append(al); alllead.append(ld[-1])
    ax.plot([], [], color='w')
allal = np.array(allal); alllead = np.array(alllead)
cc = np.corrcoef(allal, alllead)[0, 1]
ax.set_xlabel('步数'); ax.set_ylabel('沿梯度 n̂ 的前沿推进量 lead (µm)')
ax.set_title('(b) 9 晶粒 × 8 算例的竞争/淘汰\n颜色=对齐度(蓝低/红高)；corr(对齐度, lead)=%+.3f' % cc)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0.65, 1.0))
plt.colorbar(sm, ax=ax, label='取向对齐度 max|<100>·n̂|')
ax.grid(alpha=.3)
fig.suptitle('CA3D 给定条件验证 V1：包络几何/各向异性律 与 多晶竞争淘汰', fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.95])
p = os.path.join(HERE, 'FIG_validation_v1.png')
fig.savefig(p, dpi=140); print('saved', p)