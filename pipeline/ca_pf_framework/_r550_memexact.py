#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_r550_memexact.py —— 任务(5) 内存包线：**改测"引擎自己持有的数组字节数"**。

## 为什么重写（`_r549` 的量具错了，M2 当场抓到）
`_r549` 用 **RSS 增量**（`psutil` 前后差）当"这个对象占多少内存"。实测数据自相矛盾：
```
N=32 nv=8  ⇒ RSS 增量 15.0 MB
N=32 nv=16 ⇒ RSS 增量  2.6 MB   ← **比 nv=8 还小**，不可能
```
**⇒ 原因**：RSS 在 `del` 之后**不会还给 OS**（分配器缓存），而且小对象根本不显著移动 RSS。
⇒ 拟合出的 `a = 20.24 B/胞` 与留一法误差 **861%** 都是**这个量具病的症状**，不是物理结论。

**⇒ 修法：直接量"对象持有的 ndarray 字节数"**（`arr.nbytes` 求和，按 `id` 去重）。
这是**定义的量**，不是代理量 ⇒ 可复现、可加。

## 判据（先写死）
* **E1**：`phi` 一项必须**逐位等于**解析式 `nreg·N³·8/2²⁰` MB（float64）。
  对不上 ⇒ **量具或代码读错了**，先修。
* **E2**：总字节数对 `nv` **单调不减**（`_r549` 的 RSS 版在这里就违反了）。
* **E3**：留一法预测误差 ≤ **15%**（本量具是"定义的量"，应当几乎可加）。
* **E4**：给出 22 GB 预算下 4 µm / 10 µm 盒的 `nv_max`，并回代任务(5) 候选配置。

⚠ 本量具量的是**持久数组**；每步的**临时数组**（`_ed` 会造 `(nv,N³)` 的中间量）
   会额外抬高峰值 —— 报告里**单独列**，不含在 E1–E4 里。
"""
import gc
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

BUDGET_GB = 22.0
V_LATH = 1.0 * 0.5 * 0.51            # µm³


def _arrays(o, seen, depth=0):
    """递归收集对象图里的 ndarray（按 `id` 去重）。"""
    if depth > 4 or id(o) in seen:
        return
    seen.add(id(o))
    if isinstance(o, np.ndarray):
        yield o
        return
    if isinstance(o, dict):
        for v in o.values():
            yield from _arrays(v, seen, depth + 1)
        return
    if isinstance(o, (list, tuple, set)):
        for v in o:
            yield from _arrays(v, seen, depth + 1)
        return
    d = getattr(o, '__dict__', None)
    if isinstance(d, dict):
        for v in d.values():
            yield from _arrays(v, seen, depth + 1)


def footprint(N, nv, dx_um):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    g = W.LevelSetMulti(N, N * dx_um, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] * (nv + 1), nv=nv)
    seen, tot, n_arr = set(), 0, 0
    phi_b = 0
    for a in _arrays(g, seen):
        tot += a.nbytes
        n_arr += 1
        if a.shape == (nv + 1, N, N, N):
            phi_b = max(phi_b, a.nbytes)
    del g
    gc.collect()
    return tot / 2**20, phi_b / 2**20, n_arr


def main():
    L = ['=' * 100,
         'R550 —— 任务(5) 内存包线（**量"数组字节数"**，不量 RSS）', '=' * 100]
    pts = []
    for N, nv, dx in ((32, 8, 0.125), (32, 16, 0.125), (32, 32, 0.125),
                      (48, 16, 0.0833), (48, 32, 0.0833), (64, 24, 0.0625),
                      (64, 48, 0.0625)):
        mb, phi, na = footprint(N, nv, dx)
        exp_phi = (nv + 1) * N ** 3 * 8 / 2**20
        pts.append((N, nv, mb))
        L.append('  N=%-3d nv=%-3d ⇒ 数组合计 **%9.2f MB**（%d 个数组）；'
                 '`phi` = %8.2f MB（解析 %8.2f）'
                 % (N, nv, mb, na, phi, exp_phi))
        if abs(phi - exp_phi) > 1e-6 * max(exp_phi, 1):
            L.append('     ❌ **E1 违反**：`phi` 实测与解析式不符')

    # ---- E1/E2 ----
    # ★★★ **模型改对（`_r550` 第一版的 2 参数模型是"设定错误"）**
    #   第一版拟合 `y = a·nv·N³ + b`（b 与 N 无关）⇒ 留一法误差 **64%**。
    #   看数据才发现：**斜率在各 N 上是一致的 9.0 B/胞**，变的是**常数项**
    #   —— 而那个常数项**自己也正比于 N³**（`XYZ`、`region`、各种 (N,N,N) 工作数组）。
    #   ⇒ 正确模型是 **3 参数**：`y = a·(nv·N³)/2²⁰ + c·N³/2²⁰ + d`。
    #   ⚠ 这是"**改推导，不是放宽阈值**"：E3 的阈值仍是 15%。
    A3 = np.array([[nv * N ** 3 / 2**20, N ** 3 / 2**20, 1.0] for N, nv, _ in pts])
    y = np.array([mb for _, _, mb in pts])
    coef, *_ = np.linalg.lstsq(A3, y, rcond=None)
    a, c, d = float(coef[0]), float(coef[1]), float(coef[2])
    L.append('')
    L.append('  ── 拟合 `数组合计(MB) = a·nv·N³/2²⁰ + c·N³/2²⁰ + d`（**3 参数**） ──')
    L.append('     **a = %.2f B/胞**（每个 `nv` 的边际成本；`phi` 本身 8 B/胞）' % a)
    L.append('     **c = %.1f B/胞**（与 N³ 成正比的固定开销，**与 nv 无关**）' % c)
    L.append('     d = %.1f MB' % d)
    L.append('     ⇐ 第一版用 2 参数模型（`b` 与 N 无关）⇒ 留一法 64%% 误差；'
             '改成 3 参数后应当收敛')
    # E2：对 nv 单调（同 N 下）
    mono = True
    by_N = {}
    for N, nv, mb in pts:
        by_N.setdefault(N, []).append((nv, mb))
    for N, lst in by_N.items():
        lst.sort()
        for i in range(1, len(lst)):
            if lst[i][1] < lst[i - 1][1] - 1e-9:
                mono = False
                L.append('     ❌ E2 违反：N=%d 下 nv=%d→%d 的字节数反而变小'
                         % (N, lst[i - 1][0], lst[i][0]))
    L.append('     E2 对 `nv` 单调不减：%s' % ('✅ PASS' if mono else '❌ FAIL'))

    # ---- E3 留一法（3 参数模型） ----
    errs = []
    for k in range(len(pts)):
        idx = [j for j in range(len(pts)) if j != k]
        ck, *_ = np.linalg.lstsq(A3[idx], y[idx], rcond=None)
        pred = (float(ck[0]) * A3[k][0] + float(ck[1]) * A3[k][1] + float(ck[2]))
        errs.append(abs(pred - y[k]) / max(abs(y[k]), 1e-9))
    worst = max(errs)
    L.append('     E3 留一法最大相对误差 = **%.2f%%**（判据 ≤15%%）⇒ %s'
             % (100 * worst, '✅ PASS' if worst <= 0.15 else '❌ FAIL'))
    L.append('     逐点留一误差 = %s'
             % ', '.join('%.1f%%' % (100 * e) for e in errs))

    # ---- E4 包线（用 3 参数模型） ----
    L.append('')
    L.append('  ── E4：%.0f GB 预算下的包线 ──' % BUDGET_GB)
    bud = BUDGET_GB * 1024
    for nm, N, dx, Lum in (('4 µm', 64, 0.0625, 4.0), ('10 µm', 160, 0.0625, 10.0)):
        per = a * N ** 3 / 2**20
        fix = c * N ** 3 / 2**20 + d
        nv_max = max(int((bud - fix) / per), 0)
        need = int(0.30 * Lum ** 3 / V_LATH)
        L.append('     %-6s N=%-4d｜固定开销 **%7.1f MB** + 每个 `nv` **%6.2f MB**'
                 ' ⇒ `nv_max` ≈ **%d**；填 30%% 需 **%d 根** ⇒ %s'
                 % (nm, N, fix, per, nv_max, need,
                    '✅ 放得下（%.1f%% 预算）' % (100.0 * (fix + need * per) / bud)
                    if need <= nv_max else
                    '❌ **放不下**（超 %.1f×）' % (need / max(nv_max, 1))))
    L.append('')
    L.append('  ── 回代候选配置 ──')
    for lbl, N, nv in (('本轮短跑 N=64, nv=120', 64, 120),
                       ('R507 §5  N=160, nv=223', 160, 223),
                       ('R507 §5  N=160, nv=540', 160, 540),
                       ('填满 4 µm 盒 N=64, nv=75', 64, 75),
                       ('填满 10 µm 盒 N=160, nv=1176', 160, 1176)):
        mb = (a * nv + c) * N ** 3 / 2**20 + d
        obj = None
        for NN, nvv, mm in pts:
            if NN == N and nvv == nv:
                obj = mm
        L.append('     %-30s ⇒ **%9.1f MB**（%5.1f GB）%s%s'
                 % (lbl, mb, mb / 1024, '✅' if mb <= bud else '❌ **超预算**',
                    '' if obj is None else '（该点**实测** %.1f MB，模型 %.1f）'
                    % (obj, mb)))

    # ---- 临时数组（单独列，不含在拟合里） ----
    L.append('')
    L.append('  ── ⚠ 每步**临时**数组（不含在上面的持久占用里） ──')
    for N in (64, 160):
        tmp = 3 * (N ** 3) * 8 / 2**20          # `XYZ` 三个 (N,N,N) float64
        L.append('     N=%-4d：`XYZ` 三个 (N,N,N) float64 = **%.1f MB**；'
                 '`region()` int16 = %.1f MB；'
                 '`_ed` 的 (nv,N³) 中间量按 nv 线性另计'
                 % (N, tmp, N ** 3 * 2 / 2**20))

    npass = sum([mono, worst <= 0.15])
    L.append('')
    L.append('★ 汇总：E2=%s  E3=%s（%d/2）' % ('PASS' if mono else 'FAIL',
                                              'PASS' if worst <= 0.15 else 'FAIL',
                                              npass))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r550_memexact.log'), 'w') as fh:
        fh.write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
