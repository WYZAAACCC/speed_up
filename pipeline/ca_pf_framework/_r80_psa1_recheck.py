#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r80_psa1_recheck.py —— **P-SA-1 的判据量复核**（只读 F 盘原始数据，不跑仿真）。

## 为什么要复核（**新发现的量具缺陷，P1-38**）

`BLOCK_SELFAC.md §7.1 P-SA-1` 的判据是「`ed` 臂的 `r_obs` **显著低于** `random` 臂」，
`R30_AUDIT_LEDGER.md §16` 判它 **8/9 PASS**，效应量 −2.4% … −20.8%。

**但 `r_selfac` 不是一个可以跨臂直接比的量**：
    @@r_{selfac}(G)=\min_{f\in\Delta}\big\|\textstyle\sum_{i\in G}f_i\,\mathrm{dev}\,\varepsilon^0_i\big\|/\text{scale}@@
它依赖**变体集 `G` 本身** —— 不同的 `G` 有不同的**可达下界** `r_min(G)`。
而 §16 自己就记着「`ed` 的**变体数不多于** `random`」（P-SA-1c 6/6）⇒
**两臂的 `G` 不同 ⇒ 两个 `r_selfac` 不可直接相减。**

【实测例子】`_r78_pairselfac.py`：k=2 的最优对 `r_min = 0.522`，最差对 `0.9958`；
k=3 最优 `0.174`。⇒ 若 `ed` 臂恰好选中了"更好"的变体组合，
它的 `r` 更低可能**纯粹因为集合不同**，而不是"更自协调"。

## 本脚本做什么

1. 从 `dry_<tag>/snap_*.npz` + `meta.json` 读出**末态**的 `region`/`vmap`；
2. 复算实测 `f_i`、`G`、`r_selfac`（与 `blocks()` **同口径**）；
3. 用 `_r78` 的单纯形最小化求**该 `G` 的可达下界** `r_min(G)`；
4. 报**归一化残差** @@r_{norm}=(r-r_{\min})/(1-r_{\min})\in[0,1]@@
   —— `0` = 这个变体集**已经**做到最自协调；`1` = 完全没协调；
5. 用 `r_norm`（而不是裸 `r`）重判 P-SA-1a，并**同时**报裸 `r`，
   两者一致 ⇒ 原判据稳；不一致 ⇒ 原判据的结论要改。

⚠ **本脚本改不了任何归档数字**，只做重测（用户要求"用新的测量工具重新测量"）。
"""
from __future__ import annotations

import glob
import itertools
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _r78_pairselfac as R78                               # noqa: E402
from T16_verify_rve import EPS0                             # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')


def dev(A):
    A = np.asarray(A, float)
    return A - np.trace(A) / 3.0 * np.eye(3)


E_ALL = [dev(e) for e in EPS0]
SCALE = float(np.mean([np.linalg.norm(e) for e in E_ALL]))
VEC = np.array([e.reshape(-1) for e in E_ALL])              # (12, 9)


def last_snap(d):
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda p: int(re.search(r'snap_(\d+)\.npz$', p).group(1)))
    return (fs[-1], int(re.search(r'snap_(\d+)\.npz$', fs[-1]).group(1))) if fs else (None, -1)


def one(tag):
    """`tag` 可以是**完整目录名**（`eng_mb2`）或裸 tag（`mb2` ⇒ 试 `dry_`/`eng_` 前缀）。"""
    cands = [os.path.join(MB, tag)] if os.path.isdir(os.path.join(MB, tag)) else []
    for pre in ('dry_', 'eng_', ''):
        p = os.path.join(MB, pre + tag)
        if os.path.isdir(p) and p not in cands:
            cands.append(p)
    d = cands[0] if cands else os.path.join(MB, tag)
    tag = os.path.basename(d)
    if not os.path.isdir(d):
        return None
    meta = json.load(open(os.path.join(d, 'meta.json')))
    vmap = {int(k): int(v) for k, v in dict(meta['vmap']).items()}
    sp, st = last_snap(d)
    if sp is None:
        return dict(tag=tag, step=-1, err='无快照')
    reg = np.load(sp)['region']
    # ---- 实测 f_i（对**已转变**体积归一；与 `blocks()` 的 `vols` 同口径）----
    vols = {}
    for v in sorted(set(vmap.values())):
        vols[v] = float(sum(int((reg == k).sum()) for k in vmap if vmap[k] == v))
    tot = float(sum(vols.values()))
    if tot <= 0:
        return dict(tag=tag, step=st, err='无已转变体积')
    G = sorted(vols)
    f = np.array([vols[v] / tot for v in G])
    # ---- 实测 r_selfac（加权，与 `blocks()` 逐字一致）----
    acc = np.zeros((3, 3))
    for i, v in enumerate(G):
        acc = acc + f[i] * E_ALL[v - 1]
    r_obs = float(np.linalg.norm(acc)) / SCALE
    # ---- 该 G 的**可达下界**（单纯形最小化）----
    r_min = R78._simplex_r(VEC[[v - 1 for v in G]], SCALE) if len(G) > 1 \
        else float(np.linalg.norm(E_ALL[G[0] - 1])) / SCALE
    r_norm = (r_obs - r_min) / (1.0 - r_min) if r_min < 1.0 - 1e-12 else float('nan')
    # ---- 各变体自己的单变体残差（"完全不协调"的参照量）----
    r_1v = float(np.linalg.norm(acc)) / SCALE
    return dict(tag=tag, step=st, nv=len(G), G=G,
                f='/'.join('%.3f' % x for x in f),
                r_obs=r_obs, r_min=r_min, r_norm=r_norm, r_1v=r_1v,
                r_disp=float(np.linalg.norm(acc)) / SCALE)


def main():
    tags = sys.argv[1:] or ['mb2', 'mb2b', 'mb2c', 'mb3', 'mb3b', 'mb3c']
    print('=' * 116)
    print('_r80_psa1_recheck —— P-SA-1 判据量复核（`r_selfac` 的可达下界 + 归一化）')
    print('=' * 116)
    print('  SCALE = mean||dev eps0|| = %.6e' % SCALE)
    print()
    print('  %-9s %-6s %-4s %-26s %-10s %-10s %-10s %s'
          % ('tag', 'step', '#V', '实测 f_v', 'r_selfac', 'r_min(G)', 'r_norm', 'G'))
    res = {}
    for t in tags:
        r = one(t)
        if r is None:
            print('  %-9s **目录不存在**' % t)
            continue
        if r.get('err'):
            print('  %-9s %-6s **%s**' % (t, r.get('step'), r['err']))
            continue
        res[t] = r
        print('  %-9s %-6d %-4d %-26s %-10.4f %-10.4f %-10.4f %s'
              % (t, r['step'], r['nv'], r['f'], r['r_obs'], r['r_min'],
                 r['r_norm'], r['G']))
    if not res:
        return 1
    # ---- 按臂分组比 ----
    print()
    print('=' * 116)
    print('### P-SA-1a 重判：`ed`（mb2*） vs `random`（mb3*）')
    print('=' * 116)
    ed = [res[t] for t in res if 'mb2' in t]
    rd = [res[t] for t in res if 'mb3' in t]
    if not ed or not rd:
        print('  两臂数据不全，无法比')
        return 1
    print('  %-14s %-8s %-12s %-12s %s'
          % ('臂', 'n', 'mean r_selfac', 'mean r_norm', '逐次 r_norm'))
    for lab, arr in (('ed', ed), ('random', rd)):
        print('  %-14s %-8d %-12.4f %-12.4f %s'
              % (lab, len(arr), float(np.mean([a['r_obs'] for a in arr])),
                 float(np.nanmean([a['r_norm'] for a in arr])),
                 ' '.join('%.3f' % a['r_norm'] for a in arr)))
    # 配对比较（同 seed 配对；tag 尾部的 b/c 表示不同 seed）
    pairs = [('eng_mb2', 'eng_mb3'), ('eng_mb2b', 'eng_mb3b'),
             ('eng_mb2c', 'eng_mb3c')]
    print()
    print('  %-12s %-12s %-12s %-10s %-12s %-10s'
          % ('配对（同 seed）', 'Δr_selfac', 'Δr_norm', '方向(r)', '方向(r_norm)',
             '一致?'))
    n_ok_r = n_ok_n = n_pair = 0
    for a, b in pairs:
        if a not in res or b not in res:
            print('  %-12s （缺数据）' % ('%s/%s' % (a, b)))
            continue
        d_r = res[a]['r_obs'] - res[b]['r_obs']
        d_n = res[a]['r_norm'] - res[b]['r_norm']
        ok_r = d_r < 0
        ok_n = d_n < 0
        n_pair += 1
        n_ok_r += int(ok_r)
        n_ok_n += int(ok_n)
        print('  %-12s %+-12.4f %+-12.4f %-10s %-12s %s'
              % ('%s/%s' % (a, b), d_r, d_n, 'ed 更低' if ok_r else 'ed 更高',
                 'ed 更低' if ok_n else 'ed 更高',
                 '✅' if ok_r == ok_n else '⚠ **不一致**'))
    print()
    print('  ⇒ 裸 `r_selfac`：%d/%d 次 ed 更低' % (n_ok_r, n_pair))
    print('  ⇒ **归一化 `r_norm`**：%d/%d 次 ed 更低' % (n_ok_n, n_pair))
    if n_ok_r == n_ok_n:
        print('     ⇒ **原判据（§16）在归一化口径下方向一致**：结论稳住。')
    else:
        print('     ⇒ ⚠⚠ **原判据的结论在归一化口径下不成立** —— 必须改判。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
