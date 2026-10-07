#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r357_selfac_geom.py —— ★★★ 条件③的**直接**几何检验：块-块接触是否**偏好自协调（近相容）变体对**？

> **v2（本轮升级）**：v1 用 200 次**随机**置换做零分布，而置换空间只有 **6! = 720**
> ⇒ 零分布粗、p 值有抽样噪声。v2 改成
> **先把块-块接触矩阵 `Md` 算出来（几何完全不动），再对 720 个置换做穷举**
> ⇒ **零分布精确、p 值精确**，且快得多（不用每次都扫全盒）。

## 为什么这是"直接"检验

变体自协调的物理定义就是：**近相容（本征应变差接近 rank-1 不变平面应变）的变体对
更容易共存**。若组织真的自协调，块-块（异变体）接触面积应偏向
@@\\|\\varepsilon^0_a-\\varepsilon^0_b\\|@@ 小的对。
`§164` 量的是"各变体 `ed` 中位的**离散度**"；**本节量的是组织几何本身**：哪些变体对真长到了一起。

## 口径

* **块**：同一变体的**连续场**构成一块（与 `--multi-block` 播种一致；
  `1,1,2,2,3,3,4,4,7,7,8,8` ⇒ 6 块）。
* **F2 有向面**：6-邻域两侧 `region` 不同、两侧都是变体、**变体不同**。
* @@\\|\\Delta\\varepsilon\\|@@：`T16_verify_rve.EPS0` 的 Frobenius 范数（与 `§164` 同源）。
* **置换零假设**：只重排"**块 → 变体**"的标签，`region` 与几何**完全不动**
  ⇒ 控制掉"哪两块相邻、接触多少"这个混杂，剩下才是"变体选择"。

## 判据（**先写死**）

* **Y-0 自证**：重建 `argmin` == 归档 `region`（限定在 winner 的场存下来的胞上）= **1.0000**。
* **Y-1**：F2 面积按 @@\\|\\Delta\\varepsilon\\|@@ 的加权中位与分位。
* **Y-2 ★**：实测中位在 720 个置换的零分布中的**百分位**。
  **< 0.05 ⇒ 有自协调几何证据**；**否则 ❌ 无证据**。
* **Y-3**：F2 **总面积**的百分位（自协调也可能表现为"总接触面积更多"）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from itertools import permutations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MB = os.path.join(HERE, '_exp', '_bk_mb')


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def blocks_of(vk, var):
    """同一变体的**连续场** = 一块。返回 (blk_arr, blk_var)。"""
    nf = int(max(vk)) + 1
    blk_arr = np.full(nf, -1, np.int64)
    runs, cur = [], [int(vk[0])]
    for k_ in vk[1:].tolist():
        if var[k_] == var[cur[-1]]:
            cur.append(k_)
        else:
            runs.append(cur)
            cur = [k_]
    runs.append(cur)
    blk_var = []
    for bi, run in enumerate(runs):
        for k_ in run:
            blk_arr[k_] = bi
        blk_var.append(int(var[run[0]]))
    return blk_arr, np.asarray(blk_var, int)


def contact_matrix(reg, blk_arr):
    nb = int(blk_arr.max()) + 1
    Md = np.zeros((nb, nb), np.int64)
    for ax in range(3):
        b = np.roll(reg, -1, axis=ax)
        sel = reg != b
        if not sel.any():
            continue
        I = np.where(sel)
        ba = blk_arr[np.clip(reg[I], 0, blk_arr.size - 1)]
        bb = blk_arr[np.clip(b[I], 0, blk_arr.size - 1)]
        m = (ba >= 0) & (bb >= 0)
        if m.any():
            np.add.at(Md, (ba[m], bb[m]), 1)
    return Md


def wmedian(vals, cnt):
    """加权中位。"""
    o = np.argsort(vals)
    v = np.asarray(vals)[o]
    c = np.asarray(cnt)[o]
    tot = c.sum()
    if tot <= 0:
        return float('nan'), 0
    cs = np.cumsum(c)
    i = int(np.searchsorted(cs, tot / 2.0))
    return float(v[min(i, v.size - 1)]), int(tot)


def stats_for(Md, assign, DE):
    """给定"块 -> 变体"的赋值，返回 (F2 总面积, 加权中位, **加权均值**)。

    ⚠ 为什么**均值**才是主统计量（v2 第二版改）：加权**中位**只由"接触最多的那一对"决定
    ⇒ 720 个置换下只有 **4–5 个不同取值**（实测）⇒ 零分布本身就是**粗格点**，
    p 值不可信。加权**均值**用到**全部** 对的信息 ⇒ 连续、分辨力高。
    """
    nb = len(assign)
    vals, cnt = [], []
    tot = 0
    s = 0.0
    for i in range(nb):
        for j in range(nb):
            if i == j:
                continue
            n = int(Md[i, j])
            if n <= 0 or assign[i] == assign[j]:
                continue
            a, b = assign[i], assign[j]
            key = (min(a, b), max(a, b))
            vals.append(DE[key])
            cnt.append(n)
            tot += n
            s += DE[key] * n
    if not vals:
        return 0, float('nan'), float('nan')
    med, _ = wmedian(vals, cnt)
    return tot, med, s / tot


def fib_sphere(m):
    """Fibonacci 球面方向（近似均匀）。"""
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi),
                     np.cos(phi)], -1)


def rank1_residual(D, dirs):
    """@@\\min_{n,a}\\|D-\\mathrm{sym}(a\\otimes n)\\|_F@@ —— **rank-1（不变平面）相容残差**。

    自协调的**物理判据**是"本征应变差接近 rank-1 不变平面应变"，
    而不是"@@\\|\\Delta\\varepsilon\\|@@ 小"（后者只是**代理量**：
    一对可以有大的 @@\\|\\Delta\\varepsilon\\|@@ 却仍是 rank-1 相容）。
    做法：对每个单位 `n`，把 `D` 投影到 `span{sym(e_k⊗n), k=1..3}`（最小二乘），
    取残差最小者；**再做自适应步长的局部细化**。

    ⚠⚠ **第 40 个自查错误**：v2 第一版**只做网格搜索、没有细化** ⇒
    真解 `n*` 一般落在网格点之间 ⇒ **残差被高估，且高估量逐对不同**
    ⇒ 既污染了 `corr(‖Δε‖,R)=0.601`，也污染了本节的秩。
    实测（`_r373` 的 P-0）：解析 IPS 在**纯网格**下相对残差 **6.33e-2**；
    **加细化后 1.31e-7**。真实的对残差范围 = **0.000000 … 0.004514**，
    而旧口径给 **0.000434 … 0.027747**（**上限被抬高 6 倍**）。
    """
    d = D.ravel()

    def ev(n):
        A = np.zeros((9, 3))
        for k in range(3):
            e = np.zeros(3)
            e[k] = 1.0
            A[:, k] = (0.5 * (np.outer(e, n) + np.outer(n, e))).ravel()
        c, *_ = np.linalg.lstsq(A, d, rcond=None)
        r = d - A @ c
        return float(r @ r)

    bv, bn = np.inf, None
    for n in dirs:
        v = ev(n)
        if v < bv:
            bv, bn = v, n
    n = np.array(bn, float)
    rng = np.random.default_rng(3)
    step = 0.15
    for _ in range(250):
        u = rng.standard_normal(3)
        u /= np.linalg.norm(u)
        cand = n + step * u
        cand /= np.linalg.norm(cand)
        v = ev(cand)
        if v < bv:
            bv, n = v, cand
        else:
            step *= 0.94
    return float(np.sqrt(max(bv, 0.0)))


def main():
    print('=' * 108)
    print('_r357 v2 —— 条件③直接检验：块-块接触是否偏好**近相容**变体对？（720 置换穷举）')
    print('=' * 108)
    from T16_verify_rve import EPS0
    E = np.asarray([np.asarray(e, float) for e in EPS0])
    nv = E.shape[0]
    DE = {}
    D1 = {}
    dirs = fib_sphere(300)
    for a in range(1, nv + 1):
        for b in range(a + 1, nv + 1):
            Dm = E[a - 1] - E[b - 1]
            DE[(a, b)] = float(np.linalg.norm(Dm))
            D1[(a, b)] = rank1_residual(Dm, dirs)
    print('  `EPS0` 变体数 = %d；@@\\|\\Delta\\varepsilon\\|@@ 范围 = '
          '**%.6f … %.6f**（%d 对）'
          % (nv, min(DE.values()), max(DE.values()), len(DE)))
    print('  **rank-1 相容残差** @@R=\\min_{n,a}\\|D-\\mathrm{sym}(a\\otimes n)\\|@@ '
          '范围 = **%.6f … %.6f**（越小越自协调）'
          % (min(D1.values()), max(D1.values())))
    # ⚠ 代理量检验：`‖Δε‖` 与 `R` 是否一致？（若相关性低 ⇒ 必须用 R）
    kk = sorted(DE.keys())
    v1 = np.array([DE[k_] for k_ in kk])
    v2 = np.array([D1[k_] for k_ in kk])
    cc = float(np.corrcoef(v1, v2)[0, 1])
    print('  ⚠ 代理量核对：`corr(‖Δε‖, R)` = **%.3f** %s'
          % (cc, '（高度一致 ⇒ 两者可互替）' if cc > 0.9 else
             '（**不一致** ⇒ 必须用 R 作主判据）'))

    arms = []
    step_want = None
    for a_ in (sys.argv[1:] or ['saSet2']):
        if a_.startswith('step='):
            step_want = int(a_.split('=')[1])
        else:
            arms.append(a_)
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
        if step_want is not None:
            fs = [q for q in fs if int(re.search(r'_(\d+)\.npz$', q).group(1))
                  == step_want]
        if not fs:
            print('\n  %-12s ⚠ 无快照（step=%s）' % (arm, step_want))
            continue
        z = np.load(fs[-1], allow_pickle=True)
        N = int(z['N'])
        reg = np.asarray(z['region'], np.int64)
        vk = np.asarray(z['vmap_keys'], np.int64)
        vv = np.asarray(z['vmap_vals'], np.int64)
        nf = int(z['band_fld'].max()) + 1
        var = np.full(max(nf, int(vk.max()) + 1), -1, np.int64)
        var[vk] = vv
        blk_arr, blk_var = blocks_of(vk, var)
        p = rebuild(z)
        fin = np.isfinite(p)
        krec = np.argmin(np.where(fin, p, np.inf), 0)
        m_ok = fin[reg, np.arange(N)[:, None, None],
                   np.arange(N)[None, :, None], np.arange(N)[None, None, :]]
        x0 = float((krec == reg)[m_ok].mean()) if m_ok.any() else float('nan')
        print()
        print('  ### %-12s step=%-5s N=%-4d  块数=%-2d  **X-0 自证 = %.4f** %s'
              % (arm, z['step'], N, blk_var.size, x0,
                 '✅' if x0 > 0.999 else '❌ 作废'))
        if not (x0 > 0.999):
            continue
        Md = contact_matrix(reg, blk_arr)
        for lab, DD in (('‖Δε‖（代理量）', DE), ('**R（rank-1 相容残差，主判据）**', D1)):
            obs_area, obs_med, obs_mean = stats_for(Md, blk_var, DD)
            if obs_area == 0:
                print('        ⚪ 无 F2 面 ⇒ 不适用')
                break
            areas, meds, means = [], [], []
            for perm in permutations(range(blk_var.size)):
                asg = blk_var[list(perm)]
                a_, m_, mn_ = stats_for(Md, asg, DD)
                if a_ > 0:
                    areas.append(a_)
                    meds.append(m_)
                    means.append(mn_)
            areas = np.asarray(areas, float)
            meds = np.asarray(meds, float)
            means = np.asarray(means, float)
            nd = int(np.unique(np.round(means, 12)).size)
            pv = float((means <= obs_mean).mean())
            print('        **%s** F2 面 = %d；加权均值 = **%.6f**'
                  % (lab, obs_area, obs_mean))
            if nd < 5:
                print('              ❌ **不适用：零分布退化**（只有 %d 个不同取值，'
                      '块数=%d）⇒ 本臂对这个检验没有分辨力' % (nd, blk_var.size))
                continue
            print('              720 置换零分布：中位 %.6f（5–95%% = %.6f … %.6f）；'
                  '不同取值 **%d**'
                  % (float(np.median(means)), float(np.percentile(means, 5)),
                     float(np.percentile(means, 95)), nd))
            print('              实测 **%.6f** ⇒ **百分位 = %.3f** %s'
                  % (obs_mean, pv,
                     '⇒ ✅ **显著偏低 ⇒ 有自协调的几何证据**' if pv < 0.05 else
                     ('⇒ ⚠ 显著偏高（**反**自协调）' if pv > 0.95 else
                      '⇒ ❌ **与置换零假设无显著差别 ⇒ 无自协调的几何证据**')))
        var_a = float(areas.max() - areas.min()) if areas.size else 0.0
        print('        **Y-3** %s'
              % ('❌ **不适用**（F2 总面积对置换**结构性不变**：每块变体互不相同）'
                 '⇒ 本口径无分辨力' if var_a == 0.0
                 else 'F2 总面积对置换有变化（%.0f … %.0f）' % (areas.min(), areas.max())))
    print()
    print('  ⚠ 记账：置换只重排"块→变体"标签，`region`/几何**完全不动**；')
    print('     块的划分 = **同一变体的连续场**（与 `--multi-block` 播种一致）。')
    print('     ⚠ 本检验的功效受**块数**限制（6 块 ⇒ 置换空间 720，粒度粗）。')
    print('     ⚠ 它只回答"接触是否偏向近相容对"；**不回答**"驱动力是否因此更小"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
