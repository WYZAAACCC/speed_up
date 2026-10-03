#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_B2verdict.py --- ★★★★★ 问题 B 判别实验 B2 的**首次判别**（step 560/600 三臂对照）
"""
import glob
import sys
import numpy as np
from scipy import ndimage

DX = 62.5
S26 = ndimage.generate_binary_structure(3, 3)
STEPS = [int(x) for x in (sys.argv[1].split(',') if len(sys.argv) > 1
                          else '400,520,560,600'.split(','))]


def M(tag, st):
    fs = [f for f in glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag) if ('%05d' % st) in f]
    if not fs:
        return None
    with np.load(fs[0], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    fr, ar, lt = [], [], []
    for k in ks:
        m = (reg == k); n = int(m.sum())
        if n < 30:
            continue
        lab, _ = ndimage.label(m, structure=S26)
        sz = np.bincount(lab.ravel())[1:]
        if sz.size == 0:
            continue
        fr.append(sz.max() / n)
        big = (lab == (int(np.argmax(sz)) + 1))
        idx = np.argwhere(big).astype(float)
        if idx.shape[0] < 30:
            continue
        c = idx - idx.mean(0); w, v = np.linalg.eigh(c.T @ c); o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000
        ar.append(L / max(W, 1e-9)); lt.append(L / max(W, 1e-9))
    return (len(ks), 100 * float(np.median(fr)) if fr else 0,
            float(np.median(ar)) if ar else 0)


print('=' * 100)
print('★ 问题 B 判别：B2（**1 变体 · B=1**）vs 12 变体臂（**步对齐**）')
print('=' * 100)
print('  %-6s | %-22s | %-22s | %s' % ('step', 't5N276 (12变体,B=3)', 't5N276F (修复版)', 't5B2 (1变体,B=1)'))
for st in STEPS:
    cells = []
    for t in ('t5N276', 't5N276F', 't5B2'):
        r = M(t, st)
        cells.append(('场=%-3d 占比=%3.0f%% 宽比=%4.2f' % r) if r else '（无快照）')
    print('  %-6d | %-22s | %-22s | %s' % (st, cells[0], cells[1], cells[2]))
print()
print('  ── 判据（**预先写死**）──')
print('  * B2 的宽比若**保持 ≥5** ⇒ **同变体密集堆叠 / 多块是长宽比退化的原因**（B2 证实）;')
print('  * B2 的宽比若**也崩到 ~2** ⇒ **与堆叠无关**，指向更基本的机制（单根自身）;')
print('  * ⚠ 必须用**同样场数**的时点比较（B2 每档只放 1 个核 ⇒ 场数增长慢）。')
