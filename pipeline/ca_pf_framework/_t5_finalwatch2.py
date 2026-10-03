#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_finalwatch2.py --- ★★★★★ 终态自动分析（**修正版**：不用进程名判断）

## 为什么改（**我第一版错了，留痕**）
第一版用 `ps -eo args` 里找 `dry_<tag>` 判断"臂是否还在跑" ⇒
**实测它把 7 个还在跑的臂全判成"已结束"**，并记下 `step=40` 当"终态"（真终态是 1400）。
**⇒ 症状正是"量具错了和被测量对象错了长得一模一样"**（P6）。
**⚠ 而它**没有任何正对照**就上了 —— 违反本仓库第 19 条纪律（探针必须先做正对照）。**

## 修正后的判据（**自洽、不依赖进程名**）
**一个臂"已结束" ⟺ 同时满足**：
1. **它的末步连续 `STABLE_N` 次检查**完全不变**；且
2. **末步 ≥ 目标步数**（或**日志里出现结束标志**，如"提前结束于 step"）。
**⇒ 条件 1 单独不够**（跑得慢时也会"不变"）⇒ 必须与 2 同时成立。
**⇒ 而且**记录里一律带上 step**（第 29 条：给范围/上下文，别只给一个数）。
"""
import glob
import os
import re
import sys
import time
import numpy as np

DX = 62.5
ARMS = ['t5AB_A', 't5AB_B', 't5AB_C', 't5AB_D', 't5AD_500', 't5AD_700', 't5AD_1000']
TARGET = 1400          # 各臂的 `--steps`
STABLE_N = 6           # 连续 6 次（6 × 30 s = 3 min）末步不变
LOG = '_w2_t5_final_ar.log'


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def last_step(tag):
    p = '_exp/_bk_t5/dry_%s/series.csv' % tag
    try:
        with open(p) as f:
            rows = f.readlines()
        if len(rows) < 2:
            return None
        return int(rows[-1].split(',')[0])
    except Exception:
        return None


def log_says_done(tag):
    """日志里是否有"结束"标志（引擎跑完会打）"""
    p = '_w2_t5_ad_%s.log' % tag
    if not os.path.exists(p):
        p = '_w2_t5_ab_%s.log' % tag
    try:
        t = open(p, errors='ignore').read()
    except Exception:
        return False
    return bool(re.search(r'提前结束于 step|臂结束|===== 完成', t))


def measure(tag):
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
        p = [float((c @ v[:, j]).max() - (c @ v[:, j]).min() + 1) * DX / 1000.0 for j in o[:2]]
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            t = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            t = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(p[0] / max(p[1], 1e-9)); lt.append(p[0] / max(t, 1e-9))
        if t < 0.25:
            thin += 1
    if not ar:
        return None
    return dict(snapstep=st, n=len(ar),
                ar_med=float(np.median(ar)), ar_min=min(ar), ar_max=max(ar),
                lt_med=float(np.median(lt)), lt_min=min(lt), lt_max=max(lt), thin=thin)


say('════ 终态自动分析 v2（**修正判据**：末步稳定 + 达目标 / 日志结束标志）════')
say('  ⚠ 记账：v1 用进程名判断 ⇒ 把 7 个在跑的臂全判成"已结束"并记 step=40 ⇒ **已弃用 v1**')
hist = {t: [] for t in ARMS}
done = set()
for i in range(1200):                       # 1200 × 30 s ≈ 10 h
    for tag in ARMS:
        if tag in done:
            continue
        s = last_step(tag)
        hist[tag].append(s)
        if len(hist[tag]) < STABLE_N:
            continue
        tail = hist[tag][-STABLE_N:]
        stable = (None not in tail) and (len(set(tail)) == 1)
        reached = (s is not None and s >= TARGET) or log_says_done(tag)
        if stable and reached:
            m = measure(tag)
            if m is None:
                say('  ⚠ %-11s 结束（末步 %s）但**无可用快照** ⇒ 记账' % (tag, s))
            else:
                say('  ★ %-11s **终态** 末步=%-6s 快照步=%-6d 场=%-3d  '
                    '**长宽比 %.2f [%.2f, %.2f]**  **长厚比 %.2f [%.2f, %.2f]**%s'
                    % (tag, s, m['snapstep'], m['n'], m['ar_med'], m['ar_min'], m['ar_max'],
                       m['lt_med'], m['lt_min'], m['lt_max'],
                       '  ⚠ %d 个场厚<4胞(不可信)' % m['thin'] if m['thin'] else ''))
            done.add(tag)
    if len(done) == len(ARMS):
        say('════ 全部 %d 臂均已结束并记录 ⇒ 退出 ════' % len(ARMS))
        break
    time.sleep(30)
else:
    say('⚠ 超时退出（已记录 %d/%d）' % (len(done), len(ARMS)))
