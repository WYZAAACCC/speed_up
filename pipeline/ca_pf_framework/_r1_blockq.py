#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_blockq.py --- 回答"板条核能否自发形成**块**"这个问题所需的事实核对。

问题的两层含义（必须先分开）
--------------------------
① **变体意义**的块：一整片**同一变体**的区域。模型里这**可观测**（= 一个连通域）。
② **金相意义**的块：**若干根平行板条 + 它们之间的低角晶界**。
   模型只有 **12 个离散变体** ⇒ **同变体**的两根板条接触即**合并成一个连通域**
   （无能量代价、无取向差可言）⇒ **低角晶界在结构上不可表示** ⇒ 这一层**不可观测**（台账 A-5）。

本脚本核对三件事（全部来自现有产物）：
  B-1 每个多核臂的 `variants` / `nseed`（确认"多个核"是**同变体**还是**异变体**）；
  B-2 从快照看**连通分量数随步的演化**（= 合并过程）；
  B-3 末态的 **nsig / ncomp / 逐分量尺寸**（看是"合成一大片"还是"保持 N 根"）。
"""
import csv
import glob
import json
import os

import numpy as np
from scipy import ndimage as nd

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = ['e4_lath6', 'e5_equi6', 'e6_mid6', 'e7_selfac']

print('=' * 100)
print('B-1 各多核臂的播种配置')
print('-' * 100)
for d in ARMS:
    mp = os.path.join(HERE, '_exp', d, 'meta.json')
    if not os.path.exists(mp):
        print('%-12s （无 meta）' % d); continue
    m = json.load(open(mp))
    vs = m.get('variants')
    uniq = sorted(set(vs)) if isinstance(vs, (list, tuple)) else vs
    print('%-12s nseed=%-3s variants=%s  ⇒ **不同变体数=%s**'
          % (d, m.get('nseed'), vs, len(uniq) if isinstance(uniq, list) else '?'))

print('\n' + '=' * 100)
print('B-2/B-3 由快照看合并过程与末态分量结构（`nsig` = 胞数≥1% 的显著分量数）')
print('-' * 100)
for d in ARMS:
    fs = sorted(glob.glob(os.path.join(HERE, '_exp', d, 'snap_*.npz')))
    if not fs:
        print('%-12s （无快照）' % d); continue
    # 只抽样：首/中/末
    pick = [fs[0], fs[len(fs) // 2], fs[-1]]
    print('%-12s ' % d, end='')
    out = []
    for f in pick:
        z = np.load(f)
        reg = z['region']
        vals, cnts = np.unique(reg[reg > 0], return_counts=True)
        if vals.size == 0:
            out.append('step %s: 无' % z['step']); continue
        K = int(vals[np.argmax(cnts)])
        m = (reg == K)
        lab, nc = nd.label(m)
        if nc == 0:
            out.append('step %s: nc=0' % z['step']); continue
        sz = np.array(nd.sum(m, lab, range(1, nc + 1)))
        thr = 0.01 * int(m.sum())
        nsig = int((sz >= thr).sum())
        out.append('step %s: ncomp=%d **nsig=%d** 最大/%d=%.2f'
                   % (z['step'], nc, nsig, int(m.sum()), sz.max() / m.sum()))
    print(' | '.join(out))
print('=' * 100)
print('判读：若 `nsig` 从 nseed 降到 1 ⇒ **已合并成一片**（变体意义的"块"）')
print('      但"若干平行板条 + 低角晶界"那一层**模型无法表示** ⇒ 不可观测（A-5）')
print('=' * 100)
