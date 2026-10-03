#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_armon.py --- ★★★★★ 持续监控四臂的**长宽比 / 长厚比**（写进 F 盘日志）

## 用法
`python _t5_armon.py <轮次上限> <间隔秒>`（默认 60 轮 × 300 s ≈ 5 小时）
**每轮**：对 `t5AB_A/B/C/D` 取**最新快照**，用**已验证的量具**测：
* **长宽比 = p1/p2**（PCA 第 1/2 主轴跨度）
* **长厚比 = p1/p3**（厚用 **`n_hab`** 方向跨度 —— §210 定的更可靠口径）
并把**中位/范围**追加到 `_w2_t5_ar_monitor.log`。

## ⚠ 量具的有效域（§208 两级对照的结论）
* 厚度 **≥ 4 胞（≥250 nm）** 时误差 ~10% ⇒ **可用**；
* 厚度 **< 2 胞** 时不可用 ⇒ **本轮若出现极薄场，其长厚比不可信**（日志会标出）。
"""
import glob
import os
import sys
import time
import numpy as np

DX = 62.5
# ★ s215：把**还在跑的长臂**也纳入监控（用户目标 = 持续监控板条长宽比）
#   `t5V2`（N=160/10 µm，仍在跑）是当前唯一的**长臂**；`t5H3` 已跑完，留作**参照**。
TAGS = ['t5AB_A', 't5AB_B', 't5AB_C', 't5AB_D', 't5V2', 't5H3']
NROUND = int(sys.argv[1]) if len(sys.argv) > 1 else 60
GAP = int(sys.argv[2]) if len(sys.argv) > 2 else 300
LOG = '_w2_t5_ar_monitor.log'

def measure(P):
    with np.load(P, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    out = []
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        p = []
        for j in o[:2]:
            pr = c @ v[:, j]
            p.append(float(pr.max() - pr.min() + 1) * DX / 1000.0)
        if n_hab is not None:
            ax = n_hab / (np.linalg.norm(n_hab) + 1e-300)
            pr = c @ ax
            t = float(pr.max() - pr.min() + 1) * DX / 1000.0
        else:
            pr = c @ v[:, o[2]]
            t = float(pr.max() - pr.min() + 1) * DX / 1000.0
        out.append((k, idx.shape[0], p[0], p[1], t))
    return out

def say(s):
    line = '[%s] %s' % (time.strftime('%F %T'), s)
    with open(LOG, 'a') as f:
        f.write(line + '\n')
    print(line, flush=True)

say('════ 长宽比/长厚比 持续监控启动：%d 轮 × %d s ════' % (NROUND, GAP))
say('  臂 = %s   dx=%.1f nm   量具 = PCA(长/宽) + n_hab(厚)' % (TAGS, DX))
for i in range(1, NROUND + 1):
    say('──── 第 %d 轮 ────' % i)
    done = 0
    for t in TAGS:
        sn = sorted(glob.glob('_exp/_bk_t5/dry_%s/snap_*.npz' % t))
        if not sn:
            say('  %-8s （无快照）' % t)
            continue
        st = int(sn[-1].split('snap_')[1].replace('.npz', ''))
        try:
            m = measure(sn[-1])
        except Exception as e:
            say('  %-8s step %-5d ⚠ 读失败 %s' % (t, st, e))
            continue
        if not m:
            say('  %-8s step %-5d （无场）' % (t, st))
            continue
        ar = np.array([x[2] / max(x[3], 1e-9) for x in m])
        lt = np.array([x[2] / max(x[4], 1e-9) for x in m])
        thin = sum(1 for x in m if x[4] < 0.25)      # 厚度 < 4 胞 ⇒ 不可信
        say('  %-8s step %-5d 场=%-3d  **长宽比 中位 %.2f [%.2f, %.2f]**  '
            '**长厚比 中位 %.2f [%.2f, %.2f]**%s'
            % (t, st, len(m), np.median(ar), ar.min(), ar.max(),
               np.median(lt), lt.min(), lt.max(),
               '  ⚠ %d 个场厚<4胞(不可信)' % thin if thin else ''))
        done += 1
    if done == 0:
        say('  ⇒ 四臂都还没出快照（构造期）')
    time.sleep(GAP)
say('════ 监控结束（%d 轮）════' % NROUND)
