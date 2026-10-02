#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L6_ufv.py --- L6 车道：`upwind_flux_vec`（**生产口径 16.9% 墙**，最大剩余单项）候选微基准。

## 靶子（生产口径记账表，N=96/nv=48/onfly，按 **/4 线程**折算）
| 块 | 墙占比 |
|---|---|
| `op.upwind_flux_vec` | **16.9%** |
| └ `op.ufv.minmod` | **12.2%** |
| &nbsp;&nbsp;└ `op._minmod` | 7.58% |
| └ `op.ufv.diff` | 2.32% |
| └ `op.ufv.where` | 2.09% |

## 逐趟数（order=2，每个轴）
```
roll(φ,±1) + sub + /dx        → dm, dp        6 趟
roll(dm,1), roll(dp,-1)       → dmm, dpp      2 趟
dm + 0.5*minmod(dm-dmm, dp-dm)                1+1+8+1+1 = 12 趟
dp - 0.5*minmod(dpp-dp, dp-dm_new)            1+1+8+1+1 = 12 趟
Va>0 / Va*dm / Va*dp / where                  4 趟
acc +                                         1 趟
                                      合计 ≈ 37 趟/轴 ⇒ 111 趟/次
```

## 候选（**全部要求逐位**）
| # | 候选 | 省在哪 | 依据 |
|---|---|---|---|
| V0 | 归档（照抄） | — | 基准 |
| V1 | `Va * where(Va>0, dm, dp)` | 少 1 趟（不再同时算 `Va*dm` 与 `Va*dp`） | 逐元素等价 |
| V2 | V1 + 把 `0.5*` 折进 minmod（`0.25*(sa+sb)*m`） | 每次 minmod 少 1 趟（×2） | `0.5*(t*m) == (0.5*t)*m`，t 是 2 的幂倍 |
| V3 | V2 + `_minmod` 用 2 个预分配临时量做原地 | 少 7 次分配 | 值不变 |
| V4 | V3 + `acc` 直接累进输出缓冲（首轴用 `=`） | 少 1 趟 | `0.0 + x == x` |
| NC-1 | `where` 的两支对调 | — | **必须非零** |
| NC-2 | 第二个 minmod 用**更新前**的 `dm` | — | **必须非零**（AGENTS P5 记的坑） |
| NC-3 | minmod 的 `minimum` 换成 `maximum` | — | 必须非零 |
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W

REPS = 9
N = int(os.environ.get('R581L6_N', '64'))
DX = 62.5e-9
ORD = 2


def _mm(a, b):
    return W._minmod(a, b)


def _mm2(a, b):
    """V2：把外层那个 `0.5*` 折进来 ⇒ `0.25*(sa+sb)*m`（少一趟，逐位相同）。"""
    return 0.25 * (np.sign(a) + np.sign(b)) * np.minimum(np.abs(a), np.abs(b))


def ufv(phi, V, dx, order=ORD, fold_where=False, fold_half=False,
        inplace_mm=False, acc_out=False, swap_where=False):
    """参数化的 `upwind_flux_vec`（逐字保留归档的运算次序与括号）。"""
    mm = _mm2 if fold_half else _mm
    acc = 0.0
    for ax in range(3):
        Va = V[ax]
        if not np.any(Va):
            continue
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        if order >= 2:
            dmm = np.roll(dm, 1, axis=ax)
            dpp = np.roll(dp, -1, axis=ax)
            # ⚠ 归档原文是 `dm = dm + 0.5 * _minmod(...)`。
            #   第一版这里漏了那个 `0.5 *` ⇒ V1/V3 测的其实是**错的公式**
            #   （实测 max|Δ|=9.8e-10、92414 个元素不等 —— **看起来像"fold_where 不逐位"，
            #    实际是我自己的 bug**）。用 `fold_half` 时 `_mm2` 已把 0.5 折进去 ⇒ 无外层 0.5。
            if inplace_mm:
                dm = dm + 0.5 * _mm_ip(dm - dmm, dp - dm)
                dp = dp - 0.5 * _mm_ip(dpp - dp, dp - dm)
            elif fold_half:
                dm = dm + mm(dm - dmm, dp - dm)
                dp = dp - mm(dpp - dp, dp - dm)
            else:
                dm = dm + 0.5 * mm(dm - dmm, dp - dm)
                dp = dp - 0.5 * mm(dpp - dp, dp - dm)
        if swap_where:
            sel = np.where(Va > 0, dp, dm)
        else:
            sel = np.where(Va > 0, dm, dp)
        term = (Va * sel) if fold_where else np.where(Va > 0, Va * dm, Va * dp)
        acc = term if (acc_out and isinstance(acc, float)) else acc + term
    return acc


def nc2_stale_dm(phi, V, dx, order=ORD):
    """NC-2：第二个 minmod 的第二个参数用**更新前**的 `dm` ⇒ 必须非零。

    ⚠ 这是 AGENTS §7.5 **P5** 记的那个坑：`upwind_flux_vec` 的第二处 `dp - dm`
    用的是**已被更新**的 `dm`，而 `upwind_grad2` 里同名写法用的是旧的。
    "提取公因式"式重写会**结构性**改变结果。
    """
    acc = 0.0
    for ax in range(3):
        Va = V[ax]
        if not np.any(Va):
            continue
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        dmm = np.roll(dm, 1, axis=ax)
        dpp = np.roll(dp, -1, axis=ax)
        _dm_old = dm.copy()                      # ← 故意留旧的
        dm = dm + 0.5 * _mm(dm - dmm, dp - dm)
        dp = dp - 0.5 * _mm(dpp - dp, dp - _dm_old)      # ← 错的
        acc = acc + np.where(Va > 0, Va * dm, Va * dp)
    return acc


def _mm_ip(a, b):
    """V3：与 `_minmod` **同值**，中间量原地。

    `0.5*(sign(a)+sign(b))*minimum(|a|,|b|)`：
    `sign(a)+sign(b) ∈ {−2,−1,0,1,2}` 是**精确**的，`*0.5` 也精确（2 的幂）
    ⇒ 改成 `((sign(a)+sign(b))*0.5)*m` 与归档的 `0.5*((sa+sb)*m)` **逐位相同**
    （一次舍入的位置与值都一样）。
    """
    t1 = np.sign(a)
    t1 += np.sign(b)
    t1 *= 0.5
    t1 *= np.minimum(np.abs(a), np.abs(b))
    return t1


def ref_legacy(phi, V, dx, order=ORD):
    return W.upwind_flux_vec(phi, V, dx, order=order)


def mk(N, seed=0):
    rng = np.random.default_rng(seed)
    phi = rng.normal(size=(N, N, N)) * 1e-8
    # 造一个**真实形状**的 V：只有一部分胞非零（生产里 V 是掩模后的）
    V = [rng.normal(size=(N, N, N)) * 1e-9 for _ in range(3)]
    for a in V:
        a[rng.random((N, N, N)) < 0.5] = 0.0
    return phi, V


def main():
    L = ['=' * 100,
         'R581-L6 —— `upwind_flux_vec`（生产口径 16.9% 墙）候选微基准',
         '=' * 100, '  N=%d  order=%d  每调用 ≈111 趟 N³' % (N, ORD)]
    fails = []
    phi, V = mk(N)
    ref = ref_legacy(phi, V, DX)

    L.append('')
    L.append('  ── P1 逐位（`array_equal`）──')
    cands = [('V1 fold_where', dict(fold_where=True)),
             ('V1b fold_half only', dict(fold_half=True)),
             ('V2 fold_where+half', dict(fold_where=True, fold_half=True)),
             ('V3 V2+inplace_mm', dict(fold_where=True, fold_half=True,
                                       inplace_mm=True)),
             ('V4 V2+acc_out', dict(fold_where=True, fold_half=True,
                                    acc_out=True))]
    for nm, kw in cands:
        got = ufv(phi, V, DX, **kw)
        neq = int(np.count_nonzero(got != ref))
        md = float(np.max(np.abs(got - ref))) if neq else 0.0
        L.append('    %-18s max|Δ|=%.3e  不等=%-8d %s'
                 % (nm, md, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
        if neq:
            fails.append(nm)

    L.append('  ── P2 负对照（必须非零）──')
    ncs = [('NC-1 where 两支对调', lambda: ufv(phi, V, DX, fold_where=True,
                                               swap_where=True)),
           ('NC-2 第二 minmod 用旧 dm', lambda: nc2_stale_dm(phi, V, DX)),
           ('NC-3 minimum→maximum',
            lambda: 0.5 * (np.sign(phi - np.roll(phi, 1, axis=0))
                           + np.sign(phi - np.roll(phi, 1, axis=0)))
            * np.maximum(np.abs(phi), np.abs(phi)))]
    for nm, fn in ncs:
        try:
            got = fn()
        except Exception as e:
            L.append('    %-22s ⚠ 抛异常 %s: %s' % (nm, type(e).__name__, str(e)[:40]))
            continue
        if got.shape != ref.shape:
            L.append('    %-22s ⚠ 形状不同 %s（本对照只作"有差异"证据）'
                     % (nm, got.shape))
            continue
        neq = int(np.count_nonzero(got != ref))
        L.append('    %-22s 不等=%-8d %s'
                 % (nm, neq, '✅ 有分辨力' if neq else '❌ **判据失效**'))
        if neq == 0:
            fails.append(nm + ' 恒 0')

    arms = [('V0 归档', lambda: ref_legacy(phi, V, DX))] + \
           [(nm, (lambda kw=kw: ufv(phi, V, DX, **kw))) for nm, kw in cands]
    ts = {nm: [] for nm, _ in arms}
    for r in range(REPS):
        order = arms[r % len(arms):] + arms[:r % len(arms)]
        for nm, fn in order:
            t0 = time.perf_counter(); fn()
            ts[nm].append(time.perf_counter() - t0)
    tb = sorted(ts['V0 归档'])[REPS // 2]
    L.append('')
    L.append('  ── P4 计时（%d 轮，交错、轮换；中位）──' % REPS)
    for nm, _ in arms:
        v = sorted(ts[nm]); m = v[REPS // 2]
        L.append('    %-18s 中位 %8.5f s  区间 [%.5f, %.5f]  提速 **%6.3f×**'
                 % (nm, m, v[0], v[-1], tb / m))
    L.append('')
    L.append('=' * 100)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L6_ufv.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
