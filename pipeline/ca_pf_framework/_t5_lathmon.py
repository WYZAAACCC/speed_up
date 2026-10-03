#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_lathmon.py --- ★★★★★ 板条状态监控（修正"数量"口径 + 覆盖多项目标）

## 为什么必须加（**本轮发现的口径缺口**）
实测 `t5N276F` step 600：**活跃场数 = 18**，而引擎自报 **`nslab_n` = 16**
⇒ **`nslab_n` 有尺寸阈值 ⇒ 它**低估**板条数** ⇒ 用它判"数量是否足够多"会**系统性偏低**。
**⇒ 本监控**并报**两个量**（活跃场数 与 `nslab_n`），并以**活跃场数**为"已播种的板条数"。

## 报什么（一次一点，对应多个用户目标）
| 量 | 对应目标 |
|---|---|
| **活跃场数**（`region` 里非零场号个数）| **② 马氏体数量是否足够多** |
| **`nslab_n`**（引擎自报）| 同上（**并报以便对照**）|
| **每场最大连通分量占比**的中位/最小 | **碎片化程度**（新口径：**不是碎片个数**）|
| **按连通分量**的长宽比 / 长厚比的中位（只取最大分量）| **① 长宽比与长厚比** |
| **块表**（`nblk_sig` / `blk_laths` / `nf2`）| **⑤ 是否成块 ⑥ 块间是否相互影响** |
"""
import csv
import glob
import os
import sys
import time
import numpy as np
from scipy import ndimage

DX = 62.5
VOX = DX ** 3 * 1e-9
TAGS = (sys.argv[1] if len(sys.argv) > 1 else 't5N276F,t5N276').split(',')
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 600
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 120
OUT = '_w2_t5_lathmon.log'
S26 = ndimage.generate_binary_structure(3, 3)


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(OUT, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def series_last(tag):
    p = '_exp/_bk_t5/dry_%s/series.csv' % tag
    try:
        rows = list(csv.DictReader(open(p, newline='')))
        b = [r for r in rows if (r.get('nblk_sig') or '').strip()]
        return (rows[-1] if rows else None), (b[-1] if b else None)
    except Exception:
        return None, None


def snap_metrics(tag):
    fs = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not fs:
        return None
    P = fs[-1]
    st = int(P.split('snap_')[1].replace('.npz', ''))
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    if nh is not None:
        nh = nh / (np.linalg.norm(nh) + 1e-300)
    ks = sorted(int(x) for x in np.unique(reg) if x != 0)
    fr, ar, lt = [], [], []
    for k in ks:
        m = (reg == k)
        n = int(m.sum())
        if n < 30:
            continue
        lab, nc = ndimage.label(m, structure=S26)
        sizes = np.bincount(lab.ravel())[1:]
        if sizes.size == 0:
            continue
        fr.append(sizes.max() / n)
        # 只测**最大分量**的形状
        big = (lab == (int(np.argmax(sizes)) + 1))
        idx = np.argwhere(big).astype(np.float64)
        if idx.shape[0] < 30:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
        T = (float((c @ nh).max() - (c @ nh).min() + 1) * DX / 1000.0) if nh is not None \
            else float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(L / max(W, 1e-9)); lt.append(L / max(T, 1e-9))
    return dict(step=st, nfield=len(ks), fr=fr, ar=ar, lt=lt)


say('════ 板条状态监控：%s（每 %d s）════' % (TAGS, GAP))
say('  并报：活跃场数（正确口径）· nslab_n（引擎口径）· 最大分量占比 · 长宽比/长厚比 · 块表')
for _ in range(ROUNDS):
    for tag in TAGS:
        sm = snap_metrics(tag)
        row, blk = series_last(tag)
        if sm is None and row is None:
            continue
        parts = []
        if sm:
            parts.append('step=%d' % sm['step'])
            parts.append('**活跃场数=%d**' % sm['nfield'])
        if row:
            parts.append('nslab_n=%s' % row.get('nslab_n'))
        if sm and sm['fr']:
            parts.append('最大分量占比 中位=%.0f%%/最小=%.0f%%'
                         % (100 * float(np.median(sm['fr'])), 100 * min(sm['fr'])))
        if sm and sm['ar']:
            parts.append('长宽比(按最大分量)中位=**%.2f**' % float(np.median(sm['ar'])))
            parts.append('长厚比中位=%.2f' % float(np.median(sm['lt'])))
        if blk:
            parts.append('块: nblk=%s nf2=%s blk_laths=%s'
                         % (blk.get('nblk_sig'), blk.get('nf2'),
                            (blk.get('blk_laths') or '')[:18]))
        say('  [%s] %s' % (tag, ' ｜ '.join(parts)))
    time.sleep(GAP)
say('════ 监控结束 ════')
