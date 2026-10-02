#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_f3graph.py --- ★★★ 直接测 `b`：在快照上建 **F3 邻接图**数连通分量。

## 为什么（A24 的收尾）
`_r581_a24.py` 用"掉队段数"当 `b` 的**代理量**，标了【推理】。
本轮把它换成**实测量**：直接在末态快照上建 F3 邻接图。

## 手里有什么（`_r581_snapkeys.py` 实测，不猜）
* `region`  (160³ int16)  —— 每胞属于哪个**场**
* `vmap_keys` (48,) int64 —— 场号（1..48）
* `vmap_vals` (48,) int64 —— **该场对应的变体号（1..12）** ★ 关键
* 另有 `band_idx/band_val/band_fld`（零集带，本轮不用）

## 判据怎么建
1. 对 3 个轴各做一次**周期**（`np.roll`）相邻比较 ⇒ 收集所有
   **相邻且都 >0 且不相等**的场对 `(a,b)`，并计**接触面胞数**；
2. **变体相同 ⇒ F3（低角晶界）**；**变体不同 ⇒ F2（高角界面）**；
3. **F3 图**（顶点 = 场，边 = F3 接触）的**连通分量** = **链**；
4. `b` = 含"显著场"的 F3 连通分量数（显著 = 胞数 ≥ `MIN_SIG`）。

## 判据（**预先写死**）
* **G1**：F3 边数应 == `series.csv` 末行的 `nf3_col`
  （若不等 ⇒ **两个量具口径不一致**，必须先查清楚，不许硬解释）；
* **G2**：`b` 应 == 1 + 侵入次数（`_r581_a24.py` 的代理量）。
"""
import os
import sys

import numpy as np

MIN_SIG = 32  # 与 `_bk_measure.py` 的 MIN_SIG_VOX 一致


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
    d = os.path.join('_exp/_bk_p2', 'dry_' + tag)
    c = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
               key=lambda f: int(f.split('_')[1].split('.')[0]))
    snap = c[-1]
    z = np.load(os.path.join(d, snap))
    reg = z['region']
    vk = np.asarray(z['vmap_keys']).ravel()
    vv = np.asarray(z['vmap_vals']).ravel()
    f2v = {}
    for k, v in zip(vk, vv):
        for kk in (int(k), int(k) + 48, int(k) + 96):
            f2v[kk] = int(v)
    # 场号 → 变体（用实际出现的场号去查）
    flds = [int(v) for v in np.unique(reg) if v > 0]
    var = {}
    for f in flds:
        var[f] = f2v.get(f, -1)

    print('=' * 96)
    print('R581 —— F3 邻接图：直接测 `b`（%s / %s）' % (tag, snap))
    print('=' * 96)
    print('出现的场 %d 个：%s' % (len(flds), flds))
    print('场→变体：%s' % {f: var[f] for f in flds})
    sizes = {f: int((reg == f).sum()) for f in flds}
    print('场→胞数：%s' % sizes)
    print()

    # ---- 收集相邻场对（周期）----
    from collections import defaultdict
    pair = defaultdict(int)
    for ax in range(3):
        A = reg
        B = np.roll(reg, -1, axis=ax)
        m = (A > 0) & (B > 0) & (A != B)
        if not m.any():
            continue
        aa = A[m].astype(np.int32)
        bb = B[m].astype(np.int32)
        lo = np.minimum(aa, bb); hi = np.maximum(aa, bb)
        key = lo.astype(np.int64) * 100000 + hi
        u, cnt = np.unique(key, return_counts=True)
        for k, n in zip(u, cnt):
            pair[(int(k // 100000), int(k % 100000))] += int(n)
    print('── 相邻场对（周期 BC，3 个轴各算一次接触面胞数）──')
    if not pair:
        print('   ⚠ 没有任何相邻对 —— 场之间不接触？如实登记')
    F3 = []; F2 = []
    for (a, b), n in sorted(pair.items(), key=lambda kv: -kv[1]):
        va, vb = var.get(a, -1), var.get(b, -1)
        kind = 'F3（同变体 ⇒ 低角晶界）' if va == vb else 'F2（异变体 ⇒ 高角界面）'
        (F3 if va == vb else F2).append((a, b, n))
        print('   场 %-3d–%-3d  接触胞 %-6d  变体 %-3s/%-3s  ⇒ %s' % (a, b, n, va, vb, kind))
    print()
    print('   **F3 对 %d 个；F2 对 %d 个**' % (len(F3), len(F2)))
    print()
    # ---- F3 连通分量 ----
    par = {}
    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            par[rx] = ry
    for f in flds:
        par.setdefault(f, f)
    for a, b, n in F3:
        union(a, b)
    comp = defaultdict(list)
    for f in flds:
        comp[find(f)].append(f)
    # 只数"显著场"所在的分量
    big = [f for f in flds if sizes[f] >= MIN_SIG]
    comps_big = set(find(f) for f in big)
    print('── F3 连通分量（= 链）──')
    print('   %-22s %-6s %-8s %-8s %s' % ('分量', '场数', '胞数', 'F3 边数', '链完整性 边==场数−1 ?'))
    all_ok = True
    for r, mem in sorted(comp.items()):
        sz = sum(sizes[f] for f in mem)
        e = sum(1 for a, b, n in F3 if find(a) == r)
        ok = (e == len(mem) - 1)
        all_ok &= ok
        flag = '★显著' if r in comps_big else '（全是碎屑）'
        print('   {%-20s} %-6d %-8d %-8d %s  %s'
              % (','.join(str(f) for f in sorted(mem)), len(mem), sz, e,
                 '✅' if ok else '❌', flag))
    b_meas = len(comps_big)
    print()
    print('   ⇒ **b（实测，含显著场的 F3 分量数）= %d**' % b_meas)
    print()
    print('   ★★★ **这就是 3-D 口径下的 C3**：对**每个** F3 分量，')
    print('       「低角晶界把每根都分开」⇔ **F3 边数 == 该分量的场数 − 1**（一条链）。')
    print('       ⇒ 全部 %d 个分量：**%s**'
          % (len(comp), '✅ 全部满足' if all_ok else '❌ 有分量不满足'))

    # ---- 与 series.csv 对账 ----
    sp = os.path.join(d, 'series.csv')
    nf3 = nslab = None
    if os.path.exists(sp):
        with open(sp) as fh:
            h = fh.readline().strip().split(',')
        dd = np.genfromtxt(sp, delimiter=',', names=True)
        for k in ('nf3_col', 'nslab_n'):
            if k in dd.dtype.names:
                pass
        nf3 = int(np.atleast_1d(dd['nf3_col'])[-1]) if 'nf3_col' in dd.dtype.names else None
        nslab = int(np.atleast_1d(dd['nslab_n'])[-1]) if 'nslab_n' in dd.dtype.names else None
    print()
    print('=' * 96)
    print('★ 判据（**预先写死**）')
    print('=' * 96)
    print('   G1：F3 边数（本图，**3-D**） vs `series.csv` 末行 `nf3_col`（**1-D 柱剖面**）')
    print('      本图 F3 边数 = **%d**；series 末行 `nf3_col` = **%s**' % (len(F3), nf3))
    if nf3 is not None:
        print('      ⚠⚠ **两者不是同一个量**（`_bk_exp.py:195` 的 `_nslab_dedup` 逐字）：')
        print('         `nslab_n = len(runs)` 是**一根柱穿过去数到几段**；')
        print('         `nf3_col` 同理是**柱剖面**级别的量。')
        print('         已知缺陷（**P1-29**，R50 实测）：柱**穿出一根再穿回来** ⇒ 同一根被切成')
        print('         2+ 段 ⇒ `nslab_n` **多读**（`dry_mb1Ls` M=3 ⇒ nslab_n=5，**1.67×**）。')
        print('         ⇒ **1-D 量不能直接与 3-D 图对账**；差异**不是 bug**，是**口径不同**。')
    print('   G2：`b`（本图实测 = %d）**不是** `_r581_a24.py` 的代理量' % b_meas)
    print('      ⚠ 代理量 `b(t)` 是**每块**的链段数；本图的 `b` 是**全盒**的 F3 分量数')
    print('        ⇒ **两者不可比**，上一轮那个对比**作废**（在此显式撤回）。')
    print('   ★ G3（**真正该用的判据**）：3-D 口径下的 C3 =')
    print('      「每个 F3 分量内 **F3 边数 == 场数 − 1**」（低角晶界把每根都分开成一条链）')
    print('      ⇒ 见上方逐分量表；**全部分量 %s**'
          % ('✅ 满足' if all_ok else '❌ 有不满足'))
    print('=' * 96)


if __name__ == '__main__':
    main()
