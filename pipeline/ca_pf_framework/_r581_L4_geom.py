#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L4_geom.py --- L4 车道：`curvature_of` + `_bbox_pad`（`fe.advance.geom_k`，生产口径 5.25%）。

## 靶子的**实测**构成（生产口径记账表，N=96/nv=48/onfly，/4 线程折算）
| 子块 | 墙占比 |
|---|---|
| `fe.advance.geom_k` | **5.25%** |
| └ `adv.geom.curv` | 2.09% |
| └ `adv.geom.grad` | 1.78% |
| └ `adv.geom.mask_bbox` | 0.80% |
| └ `adv.geom.scatter` | 0.32% |

**⇒ 天花板很低（≈1%）**，本脚本的目标是给出**可复现的结论**，不是硬凑提速。

## goal §(6) 给的三条方向，逐条查证
① **与 `_geom_k` 已有的 `gsub/gnsub` 共用，消除重复梯度** —— **已经在 T3 做过**
   （`curvature_of(k, grad=gsub, gn=gnsub)`，`windowB_surface.py:4020`）
   ⇒ 本条**无欠账**，登记为"已完成"。
② `_bbox_pad` 的 `np.flatnonzero` → 直接在掩模上求包围盒。
   ⚠ 查证：现写法是 `np.argwhere(mask)`（**不是** `flatnonzero`）—— 它造一个
   `(M,3)` int64 索引数组（M = True 胞数）⇒ 对 20% 的掩模是 4.2 MB（N=96）。
   候选 KB1：改 `mask.any(axis=…)` 逐轴求界（3 趟 N³，不造索引数组）。
③ 三分量循环 → 一次堆叠（注意逐位兼容）。

## 候选
| # | 候选 | 依据 |
|---|---|---|
| K0 | 归档 `curvature_of`（照抄） | 基准 |
| K1 | `np.divide(..., out=)` + `np.subtract(..., out=)`（少造临时量） | 逐元素同一串运算 |
| K2 | K1 + `out` 用 `np.add(..., out=)` 累加 | `0 + x == x` |
| KB0 | 归档 `_bbox_pad`（`np.argwhere`） | 基准 |
| KB1 | 逐轴 `any` + `flatnonzero` 求界 | 同一个包围盒（**必须逐位/逐值相同**） |
| NC-1 | `pad` 少 1（必须给出**不同**的包围盒） | 必须有分辨力 |
| NC-2 | curvature 的 `±roll` 对调（正负号错） | 必须非零 |
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W

REPS = 9
N = int(os.environ.get('R581L4_N', '96'))
DX = 62.5e-9


def k0(g, gn, dx):
    out = None
    for i in range(3):
        ni = g[i] / gn
        di = (np.roll(ni, -1, axis=i) - np.roll(ni, 1, axis=i)) / (2.0 * dx)
        out = di if out is None else out + di
    return out


def k1(g, gn, dx):
    """少造临时量：`ni`/`di` 用 `out=` 复用；运算次序与括号**一字不改**。"""
    out = None
    b1 = np.empty_like(gn)
    b2 = np.empty_like(gn)
    for i in range(3):
        ni = np.divide(g[i], gn, out=b1)
        np.roll(ni, -1, axis=i, out=b2) if False else None
        a = np.roll(ni, -1, axis=i)
        b = np.roll(ni, 1, axis=i)
        di = np.subtract(a, b)
        di = np.divide(di, 2.0 * dx, out=di)
        out = di if out is None else np.add(out, di, out=out)
    return out


def kb0(mask, pad=2, wrap=True):
    return W._bbox_pad(mask, pad, wrap)


def kb1(mask, pad=2, wrap=True):
    """逐轴 `any` 求界（不造 `(M,3)` 索引数组）。**必须与 `kb0` 给出同一个包围盒。**"""
    n = np.asarray(mask.shape)
    lo = np.empty(3, np.int64)
    hi = np.empty(3, np.int64)
    touch = np.zeros(3, bool)
    for ax in range(3):
        other = tuple(a for a in range(3) if a != ax)
        line = mask.any(axis=other)              # (n[ax],)
        idx = np.flatnonzero(line)
        if idx.size == 0:
            return None
        lo[ax] = idx[0]; hi[ax] = idx[-1] + 1
        touch[ax] = (idx[0] == 0) or (idx[-1] == n[ax] - 1)
    lo = np.maximum(lo - pad, 0)
    hi = np.minimum(hi + pad, n)
    if wrap:
        lo = np.where(touch, 0, lo)
        hi = np.where(touch, n, hi)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def nc_k(g, gn, dx):
    """NC：把两个 roll 对调（符号错）⇒ 必须非零。"""
    out = None
    for i in range(3):
        ni = g[i] / gn
        di = (np.roll(ni, 1, axis=i) - np.roll(ni, -1, axis=i)) / (2.0 * dx)
        out = di if out is None else out + di
    return out


def main():
    L = ['=' * 96,
         'R581-L4 —— `curvature_of` + `_bbox_pad` 候选微基准（N=%d）' % N,
         '=' * 96,
         '  ⚠ 天花板：`fe.advance.geom_k` 生产口径只有 5.25%（curv 2.09 + grad 1.78'
         ' + mask_bbox 0.80 + scatter 0.32）']
    fails = []
    rng = np.random.default_rng(7)

    # ---- curvature_of ------------------------------------------------------
    arr = rng.normal(size=(N, N, N)) * 1e-8
    g = np.gradient(arr, DX, edge_order=2)
    gn = np.sqrt(sum(z ** 2 for z in g)) + 1e-30
    ref = k0(g, gn, DX)
    L.append('')
    L.append('  ── P1 逐位（`array_equal`）──')
    for nm, fn in (('K1 少造临时量', k1),):
        got = fn(g, gn, DX)
        neq = int(np.count_nonzero(got != ref)) + int(
            np.count_nonzero(np.signbit(got[got == 0]) != np.signbit(ref[got == 0])))
        L.append('    %-16s 不等=%-8d %s'
                 % (nm, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
        if neq:
            fails.append(nm)
    L.append('  ── P2 负对照 ──')
    nq = int(np.count_nonzero(nc_k(g, gn, DX) != ref))
    L.append('    %-16s 不等=%-8d %s' % ('NC ±roll 对调', nq,
                                         '✅ 有分辨力' if nq else '❌ 失效'))
    if not nq:
        fails.append('NC curvature')

    arms = [('K0 归档', lambda: k0(g, gn, DX)), ('K1 少临时量', lambda: k1(g, gn, DX))]
    ts = {k: [] for k, _ in arms}
    for r in range(REPS):
        order = arms[r % 2:] + arms[:r % 2]
        for nm, fn in order:
            t0 = time.perf_counter(); fn()
            ts[nm].append(time.perf_counter() - t0)
    tb = sorted(ts['K0 归档'])[REPS // 2]
    L.append('  ── P4 计时（%d 轮，交错、轮换；中位）──' % REPS)
    for nm, _ in arms:
        v = sorted(ts[nm]); m = v[REPS // 2]
        L.append('    %-16s 中位 %8.5f s  区间 [%.5f, %.5f]  提速 **%6.3f×**'
                 % (nm, m, v[0], v[-1], tb / m))

    # ---- _bbox_pad ---------------------------------------------------------
    L.append('')
    L.append('  ── `_bbox_pad`：KB1 必须给出**同一个**包围盒 ──')
    nb = 0
    for trial in range(6):
        m = rng.random((N, N, N)) < (0.02 + 0.05 * trial)
        if trial == 0:                              # 造一个碰壁的掩模（考 wrap 分支）
            m[0, :, :] = True
        if trial == 1:
            m[:, -1, :] = True
        for pad in (1, 2, 3):
            a, b = kb0(m, pad), kb1(m, pad)
            if a != b:
                nb += 1
                L.append('    ❌ trial=%d pad=%d: %s vs %s' % (trial, pad, a, b))
    L.append('    ⇒ 18 组 (6 掩模 × 3 pad) 中不一致 **%d** 组 ⇒ %s'
             % (nb, '✅ 完全一致' if nb == 0 else '❌ 有差异'))
    if nb:
        fails.append('KB1 包围盒不一致')
    # NC：pad 少 1 必须给出**不同**的盒子（证明本判据不是恒真）
    #   ⚠ 第一版用 10% 随机掩模 ⇒ 包围盒本来就撑满全盒 ⇒ `pad` 完全不影响结果
    #     ⇒ 判据**恒真**（工具报"无分辨力"）。修法：用**紧致的小团块**掩模，
    #     这样 `pad` 才会改变盒子的边界。
    m = np.zeros((N, N, N), bool)
    m[N // 3:N // 3 + 5, N // 3:N // 3 + 5, N // 3:N // 3 + 5] = True
    a2, a1, a5 = kb0(m, 2), kb0(m, 1), kb0(m, 5)
    L.append('    NC（**紧致团块** 5³）pad=2 vs pad=1：%s ；pad=2 vs pad=5：%s ⇒ %s'
             % ('相同' if a2 == a1 else '不同',
                '相同' if a2 == a5 else '不同',
                '❌ **判据恒真**' if (a2 == a1 and a2 == a5) else '✅ 有分辨力'))
    if a2 == a1 and a2 == a5:
        fails.append('NC pad 无分辨力')
    L.append('    NC（**10%% 随机**掩模）pad=2 vs pad=1：%s'
             % ('相同 ⇒ 该数据上判据退化（**正是第一版踩的坑**，已记账）'
                if kb0(rng.random((N, N, N)) < 0.1, 2) ==
                kb0(rng.random((N, N, N)) < 0.1, 1) else '不同'))

    m = rng.random((N, N, N)) < 0.2
    armb = [('KB0 argwhere', lambda: kb0(m)), ('KB1 逐轴 any', lambda: kb1(m))]
    tsb = {k: [] for k, _ in armb}
    for r in range(REPS):
        order = armb[r % 2:] + armb[:r % 2]
        for nm, fn in order:
            t0 = time.perf_counter(); fn()
            tsb[nm].append(time.perf_counter() - t0)
    tbb = sorted(tsb['KB0 argwhere'])[REPS // 2]
    L.append('  ── `_bbox_pad` 计时（掩模占 20%）──')
    for nm, _ in armb:
        v = sorted(tsb[nm]); m_ = v[REPS // 2]
        L.append('    %-16s 中位 %9.6f s  提速 **%6.3f×**' % (nm, m_, tbb / m_))

    L.append('')
    L.append('=' * 96)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L4_geom.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
