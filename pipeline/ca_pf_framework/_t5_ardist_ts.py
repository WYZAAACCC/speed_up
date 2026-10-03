#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_ardist_ts.py --- ★★★★★ 「长宽比分布」的**时间序列**（把"<3 占比"变成可跟踪的量）

## 为什么（承上一轮）
上一轮发现 `t5N276` 的长宽比**两极分化**（57% 合格 / 43% 等轴团块），
但**只有单点（step 480）** ⇒ **无法判断"团块占比是在增加还是在减少"**。
**⇒ 本脚本周期性测**每场的**长/宽/厚/两个比值**，并只把**摘要**追加到时间序列日志。**

## 摘要格式（一行一点）
`step | 场数 | 长宽比中位 | <3 占比 | 5–20 占比 | 长厚比中位 | 厚<4胞场数`
**⇒ 这样"43% 是团块"这件事就有了**趋势**（增加 = 长程变团在蔓延；减少 = 结构在改善）。**

## 口径（与既有量具一致，**已过两级对照**）
长/宽 = PCA 第 1/2 主轴跨度；厚 = 沿 `n_hab` 跨度；dx = 62.5 nm。
"""
import glob
import sys
import time
import numpy as np

DX = 62.5
TAGS = (sys.argv[1] if len(sys.argv) > 1 else 't5N276,t5NR').split(',')
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 600
ROUNDS = int(sys.argv[3]) if len(sys.argv) > 3 else 60
LOG = '_w2_t5_ardist_ts.log'


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def stat(tag):
    sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % tag))
    if not sn:
        return None
    P = sn[-1]
    st = int(P.split('snap_')[1].replace('.npz', ''))
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    ar, lt, thin = [], [], 0
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        L = float((c @ v[:, o[0]]).max() - (c @ v[:, o[0]]).min() + 1) * DX / 1000.0
        W = float((c @ v[:, o[1]]).max() - (c @ v[:, o[1]]).min() + 1) * DX / 1000.0
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            T = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            T = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(L / max(W, 1e-9)); lt.append(L / max(T, 1e-9))
        if T < 0.25:
            thin += 1
    if not ar:
        return None
    a = np.array(ar)
    return dict(step=st, n=len(a), med=float(np.median(a)),
                lt_med=float(np.median(lt)),
                frac_lo=float((a < 3).mean()), frac_ok=float(((a >= 5) & (a < 20)).mean()),
                thin=thin)


say('════ 长宽比分布**时间序列**启动：臂=%s，每 %d s ════' % (TAGS, GAP))
say('  格式：step | 场数 | 长宽比中位 | **<3 占比** | 5-20 占比 | 长厚比中位 | 厚<4胞')
for _ in range(ROUNDS):
    for tag in TAGS:
        s = stat(tag)
        if s is None:
            continue
        say('  [%s] step=%-6d 场=%-3d 长宽比中位=**%.2f**  **<3 占比=%.0f%%**  '
            '5-20 占比=%.0f%%  长厚比中位=%.2f  厚<4胞=%d'
            % (tag, s['step'], s['n'], s['med'], s['frac_lo'] * 100,
               s['frac_ok'] * 100, s['lt_med'], s['thin']))
    time.sleep(GAP)
say('════ 时间序列结束 ════')
