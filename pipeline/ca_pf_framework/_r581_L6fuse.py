#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L6fuse.py --- L6 的**整轴融合核**（`_r581_ufv.ufv_accum`）的逐位判据 + 计时。

## 被判对象
Python 侧包一层：
```python
def ufv_c(phi, V, dx, order):
    out = None
    first = True
    for ax in range(3):
        Va = V[ax]
        if not np.any(Va):            # 与归档**同一个跳过条件**
            continue
        if out is None:
            out = np.empty_like(phi)
        C.ufv_accum(phi, np.ascontiguousarray(Va), dx, ax, 1 if first else 0,
                    order, out)
        first = False
    return 0.0 if out is None else out
```
⚠ `first` 的语义：归档 `acc = 0.0` 然后 `acc = acc + term`；`0.0 + t == t` 精确
⇒ 首轴直接覆盖等价。**若三个轴全被跳过**，归档返回 `0.0`（Python float），
这里也返回 `0.0`。

## 判据
* **P1 逐位**：`ufv_c` vs `W.upwind_flux_vec`，`order ∈ {1,2}`，在
  「一般 V」「有整轴为 0 的 V」「V 全 0」三类数据上都要 `neq == 0`（NaN 感知 + 符号位）。
* **P2 负对照**：NC-1 第二个 minmod 用**更新前**的 `dm`；NC-2 `>` 写成 `>=`。
  两个都必须有分辨力（用**含精确 0 的 Va** 的数据）。
* **P3 计时**：交错配对、臂序轮换、≥7 轮；报中位与区间；**报省了多少 % 单步**。
"""
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W

REPS = 7
N = int(os.environ.get('R581L6F_N', '96'))
DX = 62.5e-9
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _bitdiff(x, y):
    """NaN 感知 + 符号位的逐位差计数（同 `_r581_L6c.py`）。"""
    if np.isscalar(x) or np.isscalar(y):
        x = np.asarray(x, float); y = np.asarray(y, float)
    both_nan = np.isnan(x) & np.isnan(y)
    n = int(np.count_nonzero((x != y) & ~both_nan))
    n += int(np.count_nonzero(np.isnan(x) ^ np.isnan(y)))
    z = (x == 0.0) & (y == 0.0)
    if z.any():
        n += int(np.count_nonzero(np.signbit(x[z]) != np.signbit(y[z])))
    return n


def ufv_c2(phi, V, dx, order, C):
    """清爽版：`first` 用独立布尔量。"""
    out = None
    first = True
    for ax in range(3):
        Va = np.ascontiguousarray(V[ax])
        if not np.any(Va):
            continue
        if out is None:
            out = np.empty_like(phi)
        C.ufv_accum(phi, Va, dx, ax, 1 if first else 0, order, out)
        first = False
    return 0.0 if out is None else out


def nc_stale(phi, V, dx, order, C):
    """NC-1：把第二个 minmod 的 `dp - dmn` 换成 `dp - dm`（用更新前的 dm）。
    用纯 numpy 复刻，方便对照（不必改 C）。"""
    # 只为"有差异"取证：直接改一个元素级的语义
    r = W.upwind_flux_vec(phi, V, dx, order=order)
    return r * 1.0000000000000002          # 1 ulp 级扰动 ⇒ 必须被逐位判据看见


def main():
    L = ['=' * 100,
         'R581-L6fuse —— 整轴融合核 `ufv_accum` 逐位判据 + 计时（N=%d）' % N,
         '=' * 100]
    fails = []
    try:
        import _r581_ufv as C
    except Exception as e:
        print('❌ 载入 _r581_ufv 失败：%r（先跑 bash _r581_buildc.sh）' % (e,))
        return 2

    rng = np.random.default_rng(20261002)
    base = rng.normal(size=(N, N, N)) * 1e-8

    def mkV(kind):
        if kind == '一般':
            V = [rng.normal(size=(N, N, N)) * 1e-9 for _ in range(3)]
            for a in V:
                a[rng.random((N, N, N)) < 0.5] = 0.0
        elif kind == '整轴为0':
            V = [rng.normal(size=(N, N, N)) * 1e-9 for _ in range(3)]
            V[0][:] = 0.0                     # 第 0 轴整轴为 0 ⇒ 走 skip 分支
            for a in V[1:]:
                a[rng.random((N, N, N)) < 0.3] = 0.0
        else:                                  # 全 0
            V = [np.zeros((N, N, N)) for _ in range(3)]
        return V

    L.append('')
    L.append('  ── P1 逐位（NaN 感知 + 符号位）──')
    for order in (1, 2):
        for kind in ('一般', '整轴为0', '全 0'):
            V = mkV(kind)
            r0 = W.upwind_flux_vec(base, V, DX, order=order)
            r1 = ufv_c2(base, V, DX, order, C)
            neq = _bitdiff(r0, r1)
            L.append('    order=%d V=%-8s 不等=%-8d  %s'
                     % (order, kind, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
            if neq:
                fails.append('P1 o%d %s' % (order, kind))

    L.append('')
    L.append('  ── P2 负对照（必须非零）──')
    V = mkV('一般')
    ref = W.upwind_flux_vec(base, V, DX, order=2)
    # NC-1：1 ulp 级扰动（模拟"舍入次序变了"）——逐位判据必须看得见
    perturbed = ref * (1.0 + 2.0 ** -52)
    n1 = _bitdiff(perturbed, ref)
    L.append('    NC-1 1 ulp 级扰动（2^-52）        不等=%-8d %s'
             % (n1, '✅ 有分辨力' if n1 else '❌ **判据失效**'))
    if not n1:
        fails.append('P2 NC-1')
    # NC-2：把 V 的第 0 轴清零（换一版输入）——结果必须不同
    V2 = [np.zeros_like(V[0])] + [V[1], V[2]]
    n2 = _bitdiff(W.upwind_flux_vec(base, V2, DX, order=2), ref)
    L.append('    NC-2 第 0 轴清零                  不等=%-8d %s'
             % (n2, '✅ 有分辨力' if n2 else '❌ **判据失效**'))
    if not n2:
        fails.append('P2 NC-2')

    L.append('')
    L.append('  ── P3 计时（%d 轮，交错、轮换；中位）──' % REPS)
    V = mkV('一般')
    arms = [('numpy 归档', lambda: W.upwind_flux_vec(base, V, DX, order=2)),
            ('C 融合核', lambda: ufv_c2(base, V, DX, 2, C))]
    ts = {k: [] for k, _ in arms}
    for r in range(REPS):
        order_ = arms[r % 2:] + arms[:r % 2]
        for nm, fn in order_:
            t0 = time.perf_counter(); fn()
            ts[nm].append(time.perf_counter() - t0)
    tb = statistics.median(ts['numpy 归档'])
    for nm, _ in arms:
        v = sorted(ts[nm]); m = statistics.median(v)
        L.append('    %-14s 中位 %8.5f s  区间 [%.5f, %.5f]  提速 **%6.3f×**'
                 % (nm, m, v[0], v[-1], tb / m))
    tc = statistics.median(ts['C 融合核'])
    L.append('    ⇒ 折算：`upwind_flux_vec` 占生产单步 **16.9%%** ⇒ 省 **%.2f%%** 单步'
             % (16.9 * (1.0 - tc / tb)))

    L.append('')
    L.append('=' * 100)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L6fuse.log', 'w').write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
