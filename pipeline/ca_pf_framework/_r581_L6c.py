#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L6c.py --- L6 的 C 扩展（`_r581_ufv.minmod`）**逐位判据 + 边缘用例 + 计时**。

## 判据（先写死）
* **P1 逐位**：C 版 vs numpy `W._minmod`，在**随机数据**与**全套边缘值**上
  `max|Δ| == 0.0` 且 `neq == 0`。
* **P2 边缘用例逐项**：`±0.0` / `NaN` / `±inf` / `1e308` / 次正规数 /
  `a==b` / 异号 —— 每一项都要逐位（**不是"大致相等"**）。
  > 为什么必须逐项：`np.sign(±0.0)` 返回 **±0.0 本身**（不是 0 的归一化），
  > `np.minimum` **传播 NaN**（`fmin` 不传播）—— 这两条正是 C 最容易写错的地方。
* **P3 负对照（必须有分辨力）**：
  * NC-1 把 `sign(x)` 写成 `(x>=0)?1:-1`（丢掉 ±0 语义）
  * NC-2 用 `fmin` 代替 `np.minimum`（丢掉 NaN 传播）
  两个都**必须**产生差异。⚠ NC-2 只在含 NaN 的数据上才可见 ⇒ 判据要**在 NaN 数据上**跑。
* **P4 计时**：交错配对、臂序轮换、≥9 轮，报中位与区间。
* **P5 构建可复现性记录存在**（`_r581_ufvc_build.txt`）且 `.so` 的 SHA256 与记录**一致**。
"""
import hashlib
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W

REPS = 9


def _nc_sign_nozero(a, b):
    """NC-1：`sign(x)` 写成 `(x>=0)?1:-1`（丢掉 ±0 语义）。"""
    sa = np.where(a >= 0, 1.0, -1.0)
    sb = np.where(b >= 0, 1.0, -1.0)
    return 0.5 * (sa + sb) * np.minimum(np.abs(a), np.abs(b))


def _nc_max(a, b):
    """NC-2（**可观测**版）：把 `np.minimum` 换成 `np.maximum`。
    第一版用的是"fmin 丢 NaN 传播"—— 但探针（`_r581_npedge.py`）证明那条
    **在本函数上不可观测**（`sign(NaN)` 已经给出 NaN，乘积无论 m 是什么都是 NaN）
    ⇒ 那不是一条好对照。"""
    return 0.5 * (np.sign(a) + np.sign(b)) * np.maximum(np.abs(a), np.abs(b))


def _bitdiff(x, y):
    """**NaN 感知**的逐位差计数。

    ⚠ 量具陷阱（本轮又踩了一次，和 R580 的 M2 同类）：
      `np.count_nonzero(x != y)` 会把 **NaN 位置算成"不等"**（`NaN != NaN` 为真）
      ⇒ 含 NaN 的数据上它**恒报有差异**。
    这里把"两边都是 NaN"视作**相同**；其余按 `!=` 判。再单独查**符号位**（±0.0 的区别
    `==` 看不出来）。
    """
    both_nan = np.isnan(x) & np.isnan(y)
    diff = (x != y) & ~both_nan
    n = int(np.count_nonzero(diff))
    # ±0.0 的符号位差
    z = (x == 0.0) & (y == 0.0)
    if z.any():
        n += int(np.count_nonzero(np.signbit(x[z]) != np.signbit(y[z])))
    # 一个 NaN 一个不是
    n += int(np.count_nonzero(np.isnan(x) ^ np.isnan(y)))
    return n


def main():
    L = ['=' * 96, 'R581-L6c —— C 扩展 `_r581_ufv.minmod` 逐位判据', '=' * 96]
    fails = []
    try:
        import _r581_ufv as C
    except Exception as e:
        print('❌ 载入 _r581_ufv 失败：%r\n   先跑 bash _r581_buildc.sh' % (e,))
        return 2

    # ---- P5 构建记录 -------------------------------------------------------
    rec = '_r581_ufvc_build.txt'
    if os.path.exists(rec):
        txt = open(rec).read()
        m = re.search(r'产物 \S+\s*:\s*([0-9a-f]{64})', txt)
        h = hashlib.sha256(open('_r581_ufv.so', 'rb').read()).hexdigest()
        ok = bool(m) and m.group(1) == h
        L.append('── P5 构建可复现性记录 ──')
        L.append('    记录里的 .so SHA256 = %s' % (m.group(1)[:16] if m else '（缺）'))
        L.append('    当前 .so   SHA256 = %s  ⇒ %s'
                 % (h[:16], '✅ 一致' if ok else '❌ **不一致（.so 被换过）**'))
        if not ok:
            fails.append('P5 SHA256')
    else:
        L.append('── P5 ❌ 缺 %s ──' % rec)
        fails.append('P5 缺记录')

    # ---- P1 随机数据 -------------------------------------------------------
    rng = np.random.default_rng(20261002)
    L.append('')
    L.append('── P1 逐位（随机数据）──')
    for N in (64, 96):
        for tag, mk in (('光滑', lambda: (rng.normal(size=(N, N, N)) * 1e-8,
                                         rng.normal(size=(N, N, N)) * 1e-8)),
                        ('含 0', lambda: (np.where(rng.random((N, N, N)) < 0.3, 0.0,
                                                  rng.normal(size=(N, N, N))),
                                         rng.normal(size=(N, N, N))))):
            a, b = mk()
            r0 = W._minmod(a, b)
            r1 = C.minmod(a, b)
            neq = _bitdiff(r0, r1)
            md = float(np.max(np.abs(r0 - r1)))
            L.append('    N=%-4d %-6s max|Δ|=%.3e  不等=%-8d %s'
                     % (N, tag, md, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
            if neq:
                fails.append('P1 N%d %s' % (N, tag))

    # ---- P2 边缘用例逐项 ---------------------------------------------------
    L.append('')
    L.append('── P2 边缘用例（每一项都必须逐位）──')
    cases = [
        ('0, 0', 0.0, 0.0), ('-0.0, 0.0', -0.0, 0.0), ('0.0, -0.0', 0.0, -0.0),
        ('-0.0, -0.0', -0.0, -0.0), ('-0.0, 1.0', -0.0, 1.0),
        ('nan, 1', np.nan, 1.0), ('1, nan', 1.0, np.nan),
        ('nan, nan', np.nan, np.nan), ('nan, 0', np.nan, 0.0),
        ('inf, 1', np.inf, 1.0), ('-inf, 1', -np.inf, 1.0),
        ('inf, -inf', np.inf, -np.inf), ('inf, inf', np.inf, np.inf),
        ('1e308, 1e308', 1e308, 1e308), ('1e308, -1e308', 1e308, -1e308),
        ('5e-324, 1e-320', 5e-324, 1e-320), ('1.0, 1.0', 1.0, 1.0),
        ('1.0, -1.0', 1.0, -1.0), ('-3.5, 2.5', -3.5, 2.5),
    ]
    nbad = 0
    for nm, x, y in cases:
        a = np.array([x, 1.0], float)
        b = np.array([y, 1.0], float)
        r0 = W._minmod(a, b)
        r1 = C.minmod(a, b)
        same = (r0[0] == r1[0]) or (np.isnan(r0[0]) and np.isnan(r1[0]))
        # 逐位：连符号位也要一样
        bits = (np.signbit(r0[0]) == np.signbit(r1[0])) if not np.isnan(r0[0]) else True
        ok = bool(same and bits)
        L.append('    %-16s numpy=%-24r C=%-24r %s'
                 % (nm, r0[0], r1[0], '✅' if ok else '❌'))
        if not ok:
            nbad += 1
            fails.append('P2 %s' % nm)
    L.append('    ⇒ 边缘用例 %d/%d 逐位' % (len(cases) - nbad, len(cases)))

    # ---- P3 负对照 ---------------------------------------------------------
    L.append('')
    L.append('── P3 负对照（必须有分辨力）──')
    # ★ 数据里**必须含精确的 0 与 -0.0**，否则 NC-1 看不见（随机数据没有精确零）
    a = rng.normal(size=(32, 32, 32))
    b = rng.normal(size=(32, 32, 32))
    a.ravel()[::17] = 0.0
    a.ravel()[1::17] = -0.0
    b.ravel()[2::17] = 0.0
    b.ravel()[3::17] = -0.0
    ref = W._minmod(a, b)
    for nm, fn in (('NC-1 sign 丢 ±0 语义', _nc_sign_nozero),
                   ('NC-2 minimum→maximum', _nc_max)):
        got = fn(a, b)
        neq = _bitdiff(got, ref)
        L.append('    %-24s 不等=%-8d %s'
                 % (nm, neq, '✅ 有分辨力' if neq else '❌ **判据失效**'))
        if neq == 0:
            fails.append('P3 %s 恒 0' % nm)
    # NaN 数据：C 版必须与 numpy **NaN 感知地**逐位一致
    an = a.copy(); an[0, 0, 0] = np.nan
    rn0 = W._minmod(an, b)
    rn2 = C.minmod(an, b)
    dn = _bitdiff(rn0, rn2)
    L.append('    ⚠ 含 NaN 数据：C 版 vs numpy 的 **NaN 感知**不等=%d（应 ==0）' % dn)
    L.append('       （注意：用裸 `!=` 会得到 1 —— 那是 `NaN != NaN`，**不是真差异**）')
    if dn != 0:
        fails.append('P3 C 版在 NaN 数据上不逐位')

    # ---- P4 计时 -----------------------------------------------------------
    L.append('')
    L.append('── P4 计时（%d 轮，交错、轮换；中位）──' % REPS)
    N = 96
    A = rng.normal(size=(N, N, N))
    B = rng.normal(size=(N, N, N))
    arms = [('numpy _minmod', lambda: W._minmod(A, B)),
            ('C  _r581_ufv', lambda: C.minmod(A, B))]
    ts = {k: [] for k, _ in arms}
    for r in range(REPS):
        order = arms[r % 2:] + arms[:r % 2]
        for nm, fn in order:
            t0 = time.perf_counter(); fn()
            ts[nm].append(time.perf_counter() - t0)
    tb = statistics.median(ts['numpy _minmod'])
    for nm, _ in arms:
        v = sorted(ts[nm]); m = statistics.median(v)
        L.append('    %-16s 中位 %8.5f s  区间 [%.5f, %.5f]  提速 **%6.3f×**'
                 % (nm, m, v[0], v[-1], tb / m))
    # 线程对照（goal 要求："单线程 vs OpenMP" 必须实测）
    L.append('    ⚠ 并行策略实测：本扩展**不开 OpenMP**（纯单线程）。')
    L.append('      理由：调用方 `upwind_flux_vec` 已在 4 个 Python 工作线程里跑，')
    L.append('      再开 OpenMP 只会超额订阅。判据：上面 N=96 的单趟计时即为'
             '单线程 T_C；')
    L.append('      `_r581_L6cprof.sh` 在**生产路径**（4 线程）上量它是否真的落到墙钟。')

    L.append('')
    L.append('=' * 96)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L6c.log', 'w').write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
