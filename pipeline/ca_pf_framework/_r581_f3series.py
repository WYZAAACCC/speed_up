#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_f3series.py --- ★★ **块形成的全过程**：对每个快照建 3-D F3 邻接图。

这是 goal §(17) 的「#2 多根是否正确堆叠成块」与「#3 块与块是否相互影响」
的**连续观测**：不看单个末态，看**块怎么长出来**。

对每个快照报：
* `blocks`（F3 分量数，含显著场） / `edges_F3` / `edges_F2`
* **链长列表**（每个分量的场数） ⇒ 看有没有"越接越长"
* **异变体接触**（F2 对）⇒ 看 #3
* 每个 F3 分量的**链完整性** `边数 == 场数−1`
"""
import os
from collections import defaultdict

import numpy as np

MIN_SIG = 32
ROOT = '_exp/_bk_p2'


def one(tag, snapfile):
    z = np.load(os.path.join(ROOT, 'dry_' + tag, snapfile))
    reg = z['region']
    step = int(z['step']) if 'step' in z else -1
    vk = np.asarray(z['vmap_keys']).ravel()
    vv = np.asarray(z['vmap_vals']).ravel()
    f2v = {}
    for k, v in zip(vk, vv):
        for off in (0, 48, 96):
            f2v[int(k) + off] = int(v)
    flds = [int(v) for v in np.unique(reg) if v > 0]
    if not flds:
        return dict(tag=tag, step=step, flds=0, sizes={}, F3=[], F2=[],
                    comps=[], nbig=0)
    var = {f: f2v.get(f, -1) for f in flds}
    sizes = {f: int((reg == f).sum()) for f in flds}
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
        u, cnt = np.unique(key, return_counts=True)
        for k, n in zip(u, cnt):
            pair[(int(k // 100000), int(k % 100000))] += int(n)
    F3 = [(a, b, n) for (a, b), n in pair.items() if var[a] == var[b]]
    F2 = [(a, b, n) for (a, b), n in pair.items() if var[a] != var[b]]
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
    big = [f for f in flds if sizes[f] >= MIN_SIG]
    comps = []
    for r, mem in comp.items():
        e = sum(1 for a, b, n in F3 if find(a) == r)
        comps.append((sorted(mem), e, sum(sizes[f] for f in mem),
                      r in set(find(f) for f in big)))
    comps.sort(key=lambda c: -len(c[0]))
    return dict(tag=tag, step=step, flds=len(flds), sizes=sizes, F3=F3, F2=F2,
                comps=comps, nbig=len(set(find(f) for f in big)), var=var)


def main():
    print('=' * 104)
    print('R581 —— 块形成的**全过程**（3-D F3 邻接图，逐快照）')
    print('=' * 104)
    for tag in ('p2_b5', 'p2_b3'):
        d = os.path.join(ROOT, 'dry_' + tag)
        if not os.path.isdir(d):
            continue
        snaps = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        print()
        print('#' * 104)
        print('# %s（%d 个快照）' % (tag, len(snaps)))
        print('#' * 104)
        print(' %-6s %-7s %-8s %-7s %-7s %-24s %s'
              % ('step', '场数', 'F3 边', 'F2 边', '块数', '链长（场数，降序）', '链完整性'))
        for s in snaps:
            r = one(tag, s)
            if r['flds'] == 0:
                print(' %-6d %-7d %-8s %-7s %-7s %s' % (r['step'], 0, '-', '-', '-', '（无场）'))
                continue
            chains = [len(c[0]) for c in r['comps'] if c[3]]
            ok = all(c[1] == len(c[0]) - 1 for c in r['comps'])
            print(' %-6d %-7d %-8d %-7d %-7d %-24s %s'
                  % (r['step'], r['flds'], len(r['F3']), len(r['F2']), r['nbig'],
                     str(chains[:8]), '✅' if ok else '❌'))
        # 末态细节
        r = one(tag, snaps[-1])
        print()
        print(' 末态（step %d）逐分量：' % r['step'])
        for mem, e, sz, isbig in r['comps']:
            va = r['var'][mem[0]]
            print('   变体 %-3s 场 %-22s 场数=%d F3边=%d 胞数=%-6d %s %s'
                  % (va, str(mem), len(mem), e, sz,
                     '✅' if e == len(mem) - 1 else '❌',
                     '★显著' if isbig else ''))
        print(' 末态 F2（异变体接触，= §(17)#3 的块间相互影响）：')
        for a, b, n in sorted(r['F2'], key=lambda x: -x[2]):
            print('   场 %-3d–%-3d  接触胞 %-6d  变体 %s/%s'
                  % (a, b, n, r['var'][a], r['var'][b]))
    print('=' * 104)


if __name__ == '__main__':
    main()
