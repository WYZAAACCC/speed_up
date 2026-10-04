#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_seven.py --- ★★★★★★ **七项监控**（用户总目标第 5 项）
   ① 形核是否正确（每档核数是否按 KM 分数律爆发+衰减）
   ② 新的形核是不是板条状（新场的形状：长宽比/厚度）
   ③ 长宽比的变化是否正确
   ④ 多个板条有没有堆叠成块（blk_laths）
   ⑤ 块与块之间有没有相互影响（nf2）
   ⑥ 块与块之间有没有产生自协调（n_var_sig + |Δed|）
   ⑦ 一个相场是否只对应一根板条（瓣数中位 / 单块场比例）
"""
import collections
import csv
import glob
import os
import re
import sys

import numpy as np
from scipy import ndimage

S26 = ndimage.generate_binary_structure(3, 3)
TAG = sys.argv[1] if len(sys.argv) > 1 else 't5FIX'
REF = 't5N276F'          # 对照（修复前）

print('=' * 104)
print('★ 七项监控：%s（修复版：--ed-eta 0.375 + --burst-km 1） vs %s（对照）' % (TAG, REF))
print('=' * 104)

# ── ① 形核是否正确 ──
print('\n① 形核是否正确（每档核数；KM 分数律应 **首档爆发 + 指数衰减**）')
for tag, lab in ((TAG, '修复版'), (REF, '对照（线性律）')):
    L = '_w2_t5_short_%s.log' % tag
    if not os.path.exists(L):
        print('   %s：（无日志）' % lab); continue
    s = open(L, errors='ignore').read()
    c = collections.Counter(re.findall(r'T=([0-9.]+) K', s))
    print('   ── %s：事件 %d ──' % (lab, sum(c.values())))
    for T, n in sorted(c.items(), key=lambda kv: -float(kv[0]))[:6]:
        print('      T = %8s K ： **%3d 个**' % (T, n))

# ── ②③④⑤⑥ 块表 ──
print('\n④⑤⑥ 块表（blk_laths / nf2 / n_var_sig）')
for tag, lab in ((TAG, '修复版'), (REF, '对照')):
    P = '_exp/_bk_t5/dry_%s/series.csv' % tag
    if not os.path.exists(P):
        print('   %s：（无数据）' % lab); continue
    rows = [r for r in csv.DictReader(open(P, newline='')) if (r.get('nblk_sig') or '').strip()]
    print('   ── %s：块表 %d 行 ──' % (lab, len(rows)))
    for r in rows[-4:]:
        print('      step %-6s nslab_n=%-4s **n_var_sig=%-3s** nblk_sig=%-4s **nf2=%-6s** blk_laths=%s'
              % (r['step'], r.get('nslab_n'), r.get('n_var_sig'), r.get('nblk_sig'),
                 r.get('nf2'), (r.get('blk_laths') or '')[:26]))

# ── ②③⑦ 逐场形状（物理量具 φ<0，26-连通分量）──
print('\n②③⑦ 逐场形状与碎裂（物理量具：`band` 的 φ<0；按 26-连通分量）')
for tag in (TAG, REF):
    fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not fs:
        print('   %s：（无快照）' % tag); continue
    print('   ── %s ──' % tag)
    for P in fs[-3:]:
        st = int(P.split('snap_')[1].replace('.npz', ''))
        with np.load(P, allow_pickle=False) as z:
            N = int(np.asarray(z['N']))
            bi = np.asarray(z['band_idx']).ravel().astype(np.int64)
            bv = np.asarray(z['band_val']).ravel()
            bf = np.asarray(z['band_fld']).ravel()
            nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
        if nh is not None:
            nh = nh / (np.linalg.norm(nh) + 1e-300)
        neg = bv < 0
        ar, nc, fr, tt = [], [], [], []
        for k in sorted(int(x) for x in np.unique(bf[neg]) if x != 0):
            sel = neg & (bf == k)
            n = int(sel.sum())
            if n < 30:
                continue
            idx = bi[sel]
            g = np.zeros((N, N, N), bool)
            g[idx // (N * N), (idx // N) % N, idx % N] = True
            lab, c = ndimage.label(g, structure=S26)
            sz = np.bincount(lab.ravel())[1:]
            nc.append(c); fr.append(100.0 * sz.max() / max(sz.sum(), 1))
            big = (lab == (int(np.argmax(sz)) + 1))
            P3 = np.argwhere(big).astype(float)
            if P3.shape[0] < 30:
                continue
            cc = P3 - P3.mean(0)
            w, v = np.linalg.eigh(cc.T @ cc)
            o = np.argsort(w)[::-1]
            L = float((cc @ v[:, o[0]]).max() - (cc @ v[:, o[0]]).min() + 1) * 62.5
            W = float((cc @ v[:, o[1]]).max() - (cc @ v[:, o[1]]).min() + 1) * 62.5
            T = float((cc @ nh).max() - (cc @ nh).min() + 1) * 62.5 if nh is not None else 0.0
            ar.append(L / max(W, 1e-9))
            if T > 0:
                tt.append(L / T)
        if not nc:
            print('      step %-6d （无场）' % st); continue
        print('      step %-6d 场=%-3d **瓣中位=%-5.1f** 最大=%-3d **占比=%.0f%%** '
              '**单块场=%d/%d** ｜ 长宽比中位=**%.2f** 长厚比中位=%.2f'
              % (st, len(nc), float(np.median(nc)), int(max(nc)), float(np.median(fr)),
                 int(sum(1 for x in nc if x == 1)), len(nc),
                 float(np.median(ar)) if ar else 0, float(np.median(tt)) if tt else 0))

# ── ⑥ |Δed| ──
print('\n⑥ 自协调：`|Δed|` 带符号（越小越接近自协调；对照基准 −2.955e8，`<0` 占 100%）')
for tag in (TAG, REF):
    L = '_w2_t5_short_%s.log' % tag
    if not os.path.exists(L):
        continue
    s = open(L, errors='ignore').read()
    hits = re.findall(r'`\|Δed\|` 中位 \*\*([0-9.e+-]+)\*\*', s)
    sg = re.findall(r'中位 ([+-][0-9.e+-]+) ｜ <0 占 \*\*([0-9.]+)%', s)
    print('   %-9s `|Δed|` 末值 = %s ｜ 带符号末值 = %s（<0 占 %s%%）'
          % (tag, hits[-1] if hits else '（无）',
             sg[-1][0] if sg else '（无）', sg[-1][1] if sg else '?'))

print('\n' + '=' * 104)
print('  判据（**预先写死**）')
print('   ① 每档核数：首档 ~63%、随后指数衰减 ⇒ **burst 正确**')
print('   ②③ 长宽比 ≥5（真实 α′ 板条 5–20）｜ 长厚比 ≥10')
print('   ④ blk_laths 出现多块（如 23/23/23）⇒ **成块**')
print('   ⑤ nf2 显著 > 0 ⇒ **块间相互影响**')
print('   ⑥ n_var_sig ≥2 且 |Δed| 明显低于对照 ⇒ **自协调**')
print('   ⑦ **瓣中位 = 1、单块场比例高** ⇒ **一个相场 = 一根板条**')
