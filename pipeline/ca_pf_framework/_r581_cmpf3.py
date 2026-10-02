#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_cmpf3.py --- ★★ **S4 / N13 的中期预告**：同一 step 上比 F3 图。

## 为什么要现在做
`p2_b5ov` / `p2_b5ps` 还在跑，但**都已有 `snap_00200.npz`**；
而 R22 实测「块在 **step 200** 就成形」⇒ **step 200 的快照已经能比**。

## ⚠ 必须先声明的口径（R33 的更正）
**所有四个臂都是 `m=4`** ⇒ **同变体板条数上限 = 4** ⇒
**本对比只能看"相对"效果（S4/N13 是否改善界面/链），不能看"绝对"水平**。
绝对水平要等 `p2_m12`（`m=12`）。

## 比什么（每项都落盘）
* **F3 / F2 边数与接触胞数**（S4 的靶子 = 界面质量）
* **F3 连通分量（链）**与**链完整性**（`边数 == 场数−1`）
* **`nf3_col` / `nslab_n` / `Vt`**（从 `series.csv` 同 step 取）
"""
import os
import sys
from collections import defaultdict

import numpy as np

ROOT = '_exp/_bk_p2'


def load(tag, step):
    d = os.path.join(ROOT, 'dry_' + tag)
    p = os.path.join(d, 'snap_%05d.npz' % step)
    if not os.path.exists(p):
        return None
    return np.load(p)


def f3graph(reg, vmap):
    flds = [int(v) for v in np.unique(reg) if v > 0]
    pair = defaultdict(int)
    for ax in range(3):
        A = reg
        B = np.roll(reg, -1, axis=ax)
        m = (A > 0) & (B > 0) & (A != B)
        if not m.any():
            continue
        aa = A[m].astype(np.int32); bb = B[m].astype(np.int32)
        lo = np.minimum(aa, bb); hi = np.maximum(aa, bb)
        key = lo.astype(np.int64) * 100000 + hi
        u, c = np.unique(key, return_counts=True)
        for k, n in zip(u, c):
            pair[(int(k // 100000), int(k % 100000))] += int(n)
    F3 = [(a, b, n) for (a, b), n in pair.items() if vmap.get(a) == vmap.get(b)]
    F2 = [(a, b, n) for (a, b), n in pair.items() if vmap.get(a) != vmap.get(b)]
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for f in flds:
        par.setdefault(f, f)
    for a, b, n in F3:
        rx, ry = find(a), find(b)
        if rx != ry:
            par[rx] = ry
    comp = defaultdict(list)
    for f in flds:
        comp[find(f)].append(f)
    return flds, F3, F2, comp


def vmap_of(z):
    vk = np.asarray(z['vmap_keys']).ravel()
    vv = np.asarray(z['vmap_vals']).ravel()
    return {int(a): int(b) for a, b in zip(vk, vv)}


def series_at(tag, step):
    p = os.path.join(ROOT, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with open(p) as fh:
        fh.readline()
    dd = np.genfromtxt(p, delimiter=',', names=True)
    st = np.atleast_1d(dd['step']).astype(int)
    i = int(np.argmin(np.abs(st - step)))
    out = {}
    for k in dd.dtype.names:
        if k in ('step', 'Vt', 'nslab_n', 'nf3_col', 'nf2'):
            out[k] = float(np.atleast_1d(dd[k])[i])
    return out


def main():
    step = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    arms = sys.argv[2:] or ['p2_b5', 'p2_b5ov', 'p2_b5ps', 'p2_b3']
    print('=' * 104)
    print('R581 —— S4 / N13 **中期预告**（step %d，F3 图口径）' % step)
    print('=' * 104)
    print('⚠ **四个臂都是 `m=4`** ⇒ 同变体上限 4 ⇒ **只看相对效果，不看绝对水平**（R33）。')
    print()
    print(' %-9s %-6s %-7s %-7s %-22s %-16s %s'
          % ('臂', '场数', 'F3边', 'F2边', '链长（场数，降序）', 'F3 链完整性', 'series：nslab/nf3/Vt'))
    for tag in arms:
        z = load(tag, step)
        if z is None:
            print(' %-9s （没有 snap_%05d.npz）' % (tag, step)); continue
        reg = z['region']
        vmap = vmap_of(z)
        flds, F3, F2, comp = f3graph(reg, vmap)
        chains = sorted((len(v) for v in comp.values()), reverse=True)
        ok = all(sum(1 for a, b, n in F3 if find_in(comp, a) is v)
                 == len(v) - 1 for v in comp.values()) if False else None
        # 逐分量核对
        par = {}
        for v in comp.values():
            for f in v:
                par[f] = tuple(sorted(v))
        bad = []
        for memb in comp.values():
            e = sum(1 for a, b, n in F3 if tuple(sorted(comp_key(comp, a))) == tuple(sorted(memb)))
            if e != len(memb) - 1:
                bad.append((sorted(memb), e, len(memb) - 1))
        s = series_at(tag, step)
        # ★★★ 单位修正（R581-R35 抓到）：`series.csv` 的 **`Vt` 是 SI（m³）**，
        #   不是 µm³。证据（`_r581_vtchk.py`，step 200）：
        #     `Vt` 原始值 = 6.193847656250003e-19 ；快照数出 2537 胞 × Δx³
        #     = 0.619385 µm³ = **6.19385e-19 m³** ⇒ **逐位吻合**。
        #   ⇒ 我此前用 `%.4f` 打印 SI 值 ⇒ 得到 `0.0000`（**同一症状出现两次**）。
        sinfo = ('%g/%g/**%.4f µm³**'
                 % (s['nslab_n'], s['nf3_col'], s['Vt'] * 1e18)) if s else '—'
        print(' %-9s %-6d %-7d %-7d %-22s %-16s %s'
              % (tag, len(flds), len(F3), len(F2), str(chains[:6]),
                 '✅ 全部' if not bad else '❌ %s' % bad[:2], sinfo))
    print()
    print('=' * 104)
    print('★ 逐对比较（同 step、只差开关）')
    print('=' * 104)
    pairs = [('p2_b5ov', 'p2_b5', 'S4：o=62.5 vs o=0'),
             ('p2_b5ps', 'p2_b5ov', 'N13：+periodic-seed 1'),
             ('p2_b5ps', 'p2_b5', 'S4+N13 合计')]
    for a, b, what in pairs:
        za, zb = load(a, step), load(b, step)
        if za is None or zb is None:
            print('  %-22s （缺快照）' % what); continue
        ra, rb = za['region'], zb['region']
        va, vb = vmap_of(za), vmap_of(zb)
        fa, F3a, F2a, ca = f3graph(ra, va)
        fb, F3b, F2b, cb = f3graph(rb, vb)
        print('  %-22s  %s → %s ： F3 边 %d→%d ； F2 边 %d→%d ； 场数 %d→%d ； 最长链 %d→%d'
              % (what, b, a, len(F3b), len(F3a), len(F2b), len(F2a),
                 len(fb), len(fa),
                 max((len(v) for v in cb.values()), default=0),
                 max((len(v) for v in ca.values()), default=0)))
        print('      F3 接触胞：%d → %d ；F2 接触胞：%d → %d'
              % (sum(n for _, _, n in F3b), sum(n for _, _, n in F3a),
                 sum(n for _, _, n in F2b), sum(n for _, _, n in F2a)))
    print('=' * 104)


def comp_key(comp, f):
    for v in comp.values():
        if f in v:
            return v
    return []


def find_in(comp, f):
    return comp_key(comp, f)


if __name__ == '__main__':
    main()
