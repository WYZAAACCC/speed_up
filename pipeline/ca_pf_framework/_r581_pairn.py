#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_pairn.py --- ★ 关键路径测量：`_pair_normals` 在**生产形状**（12 变体 × m 根）下的构造代价。

## 为什么这是关键路径
`R576_ACCT.md` 记：N=64/nv=24 构造 63.8 s，其中 `build.ncmp`（= `_pair_normals`）**32.6 s**，
并**外推**成 O(nv²)、nv=300 时 ≈1.5 h/次。任务(5) 要 nv=540 ⇒ 按该外推 **≈4.6 h/次**，
**Part 2 直接不可行**。但那是个**外推**，必须实测。

## 本脚本要回答的三个问题
Q1 `eps0` 在 `--laths` = 12 变体 × m 根时，**到底有几个互不相同的值**？
   （`_bk_exp.py:600` 是 `eps0 = [EPS0[v-1].copy() for v in laths_eff]`
     ⇒ 猜测是 12。**必须实测确认**，因为整个结论都挂在它上面。）
Q2 `_pair_normals` 的墙钟随 nv 的**真实标度**是什么？（O(nv²) 的系数是多少）
Q3 其中"**真正新算**的"与"**memo 命中**"各占多少？nv=540 时总代价多少？

## 口径
* 两种都测：**冷 memo**（本进程第一次构造，真实首次构造的情形）
  与 **热 memo**（同一进程里第二次构造，例如 smoke 之后接生产）。
* memo 键 = `(C.tobytes(), E.tobytes())`（`windowB_surface.py:844`）
  ⇒ 本脚本**用同一个 `argmin_normal_cached`**，不另写一份，保证口径一致。
* 计时用 `time.perf_counter`，每档重复 `REP` 次取**中位**。
"""
import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import windowB_surface as W
from T16_verify_rve import C, EPS0, NPF                     # noqa: E402

NVAR = len(EPS0)
REP = 3
OUT = '_r581_pairn.json'


def build_eps0(m):
    """生产形状：12 个变体各 m 根 ⇒ `--laths` = "1,1,...,2,2,...,12,12,..."。"""
    return [np.asarray(EPS0[v - 1], float).copy()
            for v in range(1, NVAR + 1) for _ in range(m)]


def n_distinct(eps0):
    seen = set()
    for e in eps0:
        seen.add(np.asarray(e, float).tobytes())
    return len(seen)


def time_call(fn, rep=REP):
    ts = []
    for _ in range(rep):
        t0 = time.perf_counter()
        r = fn()
        ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2], r


def main():
    res = {'nvar': NVAR, 'rep': REP, 'rows': [], 'verdict': {}}
    print('=' * 78)
    print('Q1  `eps0` 的互异值个数（生产形状 12 变体 × m）')
    print('=' * 78)
    for m in (1, 2, 6, 45):
        e = build_eps0(m)
        nd = n_distinct(e)
        n = len(e)
        print('  m=%-3d nv=%-4d  互异 eps0 = %-3d  （若 =12 则证实"12 变体复制"）'
              % (m, n, nd))
        res.setdefault('q1', []).append({'m': m, 'nv': n, 'n_distinct': nd})

    print()
    print('=' * 78)
    print('Q2/Q3  `_pair_normals` 墙钟 vs nv')
    print('       npair = nv(nv-1)/2；其中**互异的 de** 由 Q1 决定')
    print('=' * 78)
    hdr = ('  %-6s %-6s %-9s %-11s %-11s %-11s %-8s' %
           ('m', 'nv', 'npair', 'cold(s)', 'warm(s)', 'cold/npair', 'us/pair'))
    print(hdr)
    print('  ' + '-' * (len(hdr) - 2))
    for m in (1, 2, 4, 8, 12, 20, 30, 45):
        eps0 = build_eps0(m)
        nv = len(eps0)
        npair = nv * (nv - 1) // 2
        # 冷：清空 memo，只留"真正新算"的那部分代价
        W._ARG_NORMAL_CACHE.clear()
        cold, _ = time_call(lambda: W.LevelSetMulti._pair_normals(C, eps0), rep=1)
        # 热：memo 已满（这就是"同进程第二次构造"的代价）
        warm, tab = time_call(lambda: W.LevelSetMulti._pair_normals(C, eps0), rep=REP)
        print('  %-6d %-6d %-9d %-11.4f %-11.4f %-11.3e %-8.1f'
              % (m, nv, npair, cold, warm, cold / max(npair, 1),
                 1e6 * warm / max(npair, 1)))
        res['rows'].append({'m': m, 'nv': nv, 'npair': npair,
                            'cold_s': cold, 'warm_s': warm,
                            'cache_entries': len(W._ARG_NORMAL_CACHE)})
        sys.stdout.flush()

    # ---- 标度律拟合（热路径，看 O(nv^p) 的 p）--------------------------------
    rows = [r for r in res['rows'] if r['nv'] >= 24]
    if len(rows) >= 2:
        a = np.array([r['nv'] for r in rows], float)
        b = np.array([r['warm_s'] for r in rows], float)
        p = np.polyfit(np.log(a), np.log(b), 1)
        print()
        print('  热路径拟合： warm_s ≈ %.3e · nv^%.3f' % (np.exp(p[1]), p[0]))
        res['warm_exponent'] = float(p[0])
        res['warm_coef'] = float(np.exp(p[1]))

    # ---- 生产形状 nv=540 的预测 ---------------------------------------------
    print()
    print('=' * 78)
    print('★ 生产 nv=540 的预测（用上面实测拟合，不用 R576 的旧外推）')
    print('=' * 78)
    pred = None
    if 'warm_exponent' in res:
        pred = res['warm_coef'] * 540 ** res['warm_exponent']
        print('  热 memo（同进程第二次构造）  ≈ %.1f s = %.2f min'
              % (pred, pred / 60))
        res['pred_nv540_warm_s'] = pred
    # 冷 memo 的"新增部分" = 66 个互异对（12 变体）→ 由小 nv 的实测直接读
    cold12 = None
    for r in res['rows']:
        if r['nv'] == 12:
            cold12 = r['cold_s']
    if cold12 is not None:
        print('  冷 memo：12 变体只有 **66 个互异对**（Q1 已证互异 eps0=12）')
        print('           ⇒ 与 nv=12 那次冷构造的新增计算量**相同** = %.4f s' % cold12)
        print('           ⇒ 冷构造成本 ≈ 66 对的新算 + nv=540 的循环开销')
        res['cold_nv12_s'] = cold12
        if pred is not None:
            tot = pred + cold12
            print('  ★ nv=540 首次构造 `build.ncmp` 合计 ≈ %.1f s = %.2f min'
                  % (tot, tot / 60))
            res['pred_nv540_total_s'] = tot
            res['feasible'] = bool(tot < 1800)
            print('  ★ 可行性（判据：< 30 min）：%s'
                  % ('✅ 可行' if tot < 1800 else '❌ 不可行，需改'))

    json.dump(res, open(OUT, 'w'), indent=1, ensure_ascii=False)
    print()
    print('  已写 %s' % OUT)


if __name__ == '__main__':
    main()
