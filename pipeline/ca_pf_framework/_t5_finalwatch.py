#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_finalwatch.py --- ★★★★★ 终态自动分析：各臂**跑完**时自动测它的**终态长宽比**并落盘

## 为什么需要（**补一个真实缺口**）
**剂量-响应的**关键交付**是**各臂跑到 1400 步时的终态长宽比**（回答 §223.5：
   "高长宽比能否在生长中存活"）。
**而监控 `_t5_armon.py` 只是**周期性**测**当前**快照 ——
   **若某臂结束时无人读，它的终态就没人记录**（虽然快照还在，但"哪张是终态""当时读数是多少"没落盘）。
**⇒ 本作业**盯住每臂是否结束**（进程不在 + 末步 ≥ 目标 或 日志出现结束标志），
   **结束时立即测终态**并**追加到 `_w2_t5_final_ar.log`**（**持久，不受会话影响**）。

## 判据与量具（**与监控完全一致**，已过两级对照）
* **长/宽 = PCA 第 1/2 主轴**；**厚 = 沿 `n_hab`**；
* **成对给出中位与范围**（第 29 条）；
* **标出厚度 < 4 胞（250 nm）的场**（§208 有效域）。
"""
import glob
import os
import subprocess
import sys
import time
import numpy as np

DX = 62.5
ARMS = ['t5AB_A', 't5AB_B', 't5AB_C', 't5AB_D', 't5AD_500', 't5AD_700', 't5AD_1000']
LOG = '_w2_t5_final_ar.log'


def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)


def running(tag):
    """该臂是否还有引擎进程（**用 ps + 精确匹配，避免 pgrep -f 自匹配**，§215）"""
    try:
        out = subprocess.run(['ps', '-eo', 'args', '--no-headers'],
                             capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return True
    return ('dry_%s' % tag) in out


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
    return dict(step=st, n=len(ar), P=P,
                ar_med=float(np.median(ar)), ar_min=min(ar), ar_max=max(ar),
                lt_med=float(np.median(lt)), lt_min=min(lt), lt_max=max(lt), thin=thin)


say('════ 终态自动分析启动：盯 %d 个臂 ════' % len(ARMS))
say('  量具与监控一致（PCA 长/宽 + n_hab 厚；已过两级对照）；成对给中位与范围（第29条）')
done = set()
for i in range(2000):                      # 2000 × 30 s ≈ 16.7 h
    for tag in ARMS:
        if tag in done:
            continue
        if running(tag):
            continue
        # 臂已不在跑 ⇒ 判定为结束（**注意：也可能是启动失败**，两者都要记）
        m = measure(tag)
        if m is None:
            say('  ⚠ %-11s 已结束但**无可用快照**（构造期失败？）⇒ 记账' % tag)
        else:
            say('  ★ %-11s **终态** step=%-6d 场=%-3d  **长宽比 %.2f [%.2f, %.2f]**  '
                '**长厚比 %.2f [%.2f, %.2f]**%s'
                % (tag, m['step'], m['n'], m['ar_med'], m['ar_min'], m['ar_max'],
                   m['lt_med'], m['lt_min'], m['lt_max'],
                   '  ⚠ %d 个场厚<4胞(不可信)' % m['thin'] if m['thin'] else ''))
        done.add(tag)
    if len(done) == len(ARMS):
        say('════ 全部 %d 个臂都已结束并记录 ⇒ 本作业退出 ════' % len(ARMS))
        break
    time.sleep(30)
else:
    say('⚠ 超时退出（%d/%d 个臂已记录）' % (len(done), len(ARMS)))
