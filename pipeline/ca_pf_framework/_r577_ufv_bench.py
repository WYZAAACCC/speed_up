#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r577_ufv_bench.py --- `upwind_flux_vec` 重写的**候选微基准 + 逐位判据**。

## 为什么先做微基准再改生产代码

`_r576` 的记账表把这一项顶到了第一名：`op.ufv.minmod` = **31.1%** 的单步、
`op._minmod` 17.9%、`op.ufv.diff` 6.5%。但"哪一版更快"**不能靠读代码断言** ——
本仓库已经栽过多次（`Lam` 转置在 Windows 上 1.46× 而 Linux 上只有 1.03×；
`optimize=True` 反而 0.58×）。⇒ 先在这里把候选跑一遍、把**逐位差**一起量出来。

## 候选

* `legacy`   —— 生产现值（`np.roll` ×4 + `_minmod` ×2，公式不动）
* `slices`   —— **切片移位 + 原地运算**，公式**一字不改** ⇒ **必须逐位相同**
* `fused`    —— 在 `slices` 基础上把 `_minmod` 换成 `np.where(|a|<=|b|, a, b)` 型
                （值相同、**±0.0 的符号可能不同**）⇒ 预期**非逐位**，只作参考

判据（先写死）：
  * `slices` vs `legacy`：`max|Δ|/max|ref|` **必须 0.000e+00**，否则不许上线。
  * `fused`  ：允许非零，但必须给出实测数（并且**不作为生产候选**，除非另立判据）。
  * 加速比：在 N=64（生产算例的盒尺寸）上、**同进程交错**取中位。
"""
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                     # noqa: E402

N = int(os.environ.get('R577_N', '64'))
REPS = int(os.environ.get('R577_REPS', '15'))
AXES = 3


# --------------------------------------------------------------- 候选实现
def _shift0(a, out, k):
    """`out[i] = a[i+k]`（沿 axis 0，周期）。k=±1。"""
    if k > 0:
        out[:-k] = a[k:]
        out[-k:] = a[:k]
    else:
        j = -k
        out[j:] = a[:-j]
        out[:j] = a[-j:]
    return out


def _minmod_inplace(a, b):
    """与 `W._minmod` **同公式**，只把中间量改成原地运算。

    `0.5*(sign(a)+sign(b))*minimum(|a|,|b|)`：
      * `s = sign(a)`、`s += sign(b)` —— `s` 是新建的，后面全部原地
      * `s *= 0.5` 再 `s *= m`（**次序与 `0.5*(sa+sb)*m` 不同**，但
        `sa+sb ∈ {−2,−1,0,1,2}` 是**精确**整数、乘 0.5 与乘 m 都**无舍入**
        （m 是 `min(|a|,|b|)` 本身，不是新算出来的）⇒ 结果逐位相同）
    """
    s = np.sign(a)
    s += np.sign(b)
    s *= 0.5
    m = np.minimum(np.abs(a), np.abs(b))
    s *= m
    return s


def ufv_legacy(phi, V, dx, order=1):
    return W.upwind_flux_vec(phi, V, dx, order=order)


def ufv_slices(phi, V, dx, order=1):
    """★ v1 有个**布局 bug**：`Va = V[ax]` 是**原始轴序**，而 `dm/dp` 是从
    `np.moveaxis(phi, ax, 0)` 算出来的**移动后轴序** ⇒ `Va * dm` 两个布局混用。
    实测后果 `max|Δ|/max = 7.08e-01`（不是舍入，是结构性错位）。
    ⇒ 修法：`Va` 也 `moveaxis` 到同一布局。**这就是"逐位判据"必须存在的原因** ——
    只看"快了多少"会把这个错当成一次成功的优化。"""
    acc = None
    s1 = None
    for ax in range(AXES):
        Va0 = V[ax]
        if not np.any(Va0):
            continue
        Va = np.moveaxis(Va0, ax, 0)
        a = np.moveaxis(phi, ax, 0)
        if s1 is None:
            s1 = np.empty(a.shape, dtype=a.dtype)
            dm = np.empty(a.shape, dtype=a.dtype)
            dp = np.empty(a.shape, dtype=a.dtype)
            t1 = np.empty(a.shape, dtype=a.dtype)
            t2 = np.empty(a.shape, dtype=a.dtype)
            t3 = np.empty(a.shape, dtype=a.dtype)
        # dm = (a - a[i-1]) / dx      ← 与 (phi - roll(phi,1))/dx 同两步
        _shift0(a, s1, -1)
        np.subtract(a, s1, out=dm)
        dm /= dx
        # dp = (a[i+1] - a) / dx
        _shift0(a, s1, 1)
        np.subtract(s1, a, out=dp)
        dp /= dx
        if order >= 2:
            _shift0(dm, s1, -1)
            np.subtract(dm, s1, out=t1)          # dm - dmm
            np.subtract(dp, dm, out=t2)          # dp - dm_old
            _shift0(dp, s1, 1)
            np.subtract(s1, dp, out=t3)          # dpp - dp
            m1 = _minmod_inplace(t1, t2)
            m1 *= 0.5
            np.add(dm, m1, out=dm)               # dm ← 新 dm
            np.subtract(dp, dm, out=t2)          # ★ R577：必须**用新的 dm** 重算
            m2 = _minmod_inplace(t3, t2)
            m2 *= 0.5
            np.subtract(dp, m2, out=dp)
        contrib = np.where(Va > 0, Va * dm, Va * dp)
        if acc is None:
            acc = np.zeros(phi.shape)
            accv = np.moveaxis(acc, ax, 0)
            np.add(accv, contrib, out=accv)      # 与 `0.0 + contrib` 同（−0.0 → +0.0）
        else:
            accv = np.moveaxis(acc, ax, 0)
            np.add(accv, contrib, out=accv)
    if acc is None:
        return 0.0
    return acc


def ufv_rollip(phi, V, dx, order=1):
    """**最小改动候选**：`np.roll` 与整体公式**一字不动**，只把 `_minmod` 换成
    同公式的原地版、并把 `dm = dm + 0.5*m1` 换成原地加。

    为什么先试这条：`_r576` 的表显示 `op.ufv.minmod` 占 **31.1%** 而
    `op.ufv.diff`（4 次 `np.roll`）只占 **6.5%** ⇒ **瓶颈在 minmod 的中间量，不在 roll**。
    ⇒ 应该先把 minmod 的 8 个临时量压到 3 个，而不是去动 roll。"""
    acc = 0.0
    for ax in range(AXES):
        Va = V[ax]
        if not np.any(Va):
            continue
        dm = (phi - np.roll(phi, 1, axis=ax)) / dx
        dp = (np.roll(phi, -1, axis=ax) - phi) / dx
        if order >= 2:
            dmm = np.roll(dm, 1, axis=ax)
            dpp = np.roll(dp, -1, axis=ax)
            m1 = _minmod_inplace(dm - dmm, dp - dm)
            m1 *= 0.5
            dm += m1
            # ★★★ R577 抓到的**语义细节**（生产代码里的隐式行为，必须原样保留）：
            #   原式是
            #       dm = dm + 0.5*_minmod(dm - dmm, dp - dm)
            #       dp = dp - 0.5*_minmod(dpp - dp, dp - dm)
            #   第二行里的 `dm` **已经是新的 `dm`**（第一行 rebinding 过了）⇒
            #   第二个 minmod 的第二个参数是 `dp - dm_new`，**不是** `dp - dm_old`。
            #   ⚠ 对比：`upwind_grad2` 写的是 `Dm2 = …` / `Dp2 = …`（新名字）⇒
            #     那里两处都用 `dp - dm_old`。**两个函数在这一点上并不一致**，
            #     而 `proj2`（生产默认）走的是 `upwind_flux_vec`。
            #   我第一版把 `dp - dm` 提出来复用 ⇒ `max|Δ|/max = 4.77e-02`
            #     （不是舍入，是**结构性**差异）⇒ 逐位判据直接抓住。
            m2 = _minmod_inplace(dpp - dp, dp - dm)      # ← dm 是**新的**
            m2 *= 0.5
            dp -= m2
        acc = acc + np.where(Va > 0, Va * dm, Va * dp)
    return acc


def ufv_fused(phi, V, dx, order=1):
    """`slices` + `np.where` 型 minmod（**值等价、±0.0 可能不同**）。"""
    acc = None
    s1 = None
    for ax in range(AXES):
        Va = V[ax]
        if not np.any(Va):
            continue
        a = np.moveaxis(phi, ax, 0)
        if s1 is None:
            s1 = np.empty(a.shape, dtype=a.dtype)
            dm = np.empty(a.shape, dtype=a.dtype)
            dp = np.empty(a.shape, dtype=a.dtype)
            t1 = np.empty(a.shape, dtype=a.dtype)
            t2 = np.empty(a.shape, dtype=a.dtype)
            t3 = np.empty(a.shape, dtype=a.dtype)
        _shift0(a, s1, -1)
        np.subtract(a, s1, out=dm)
        dm /= dx
        _shift0(a, s1, 1)
        np.subtract(s1, a, out=dp)
        dp /= dx
        if order >= 2:
            _shift0(dm, s1, -1)
            np.subtract(dm, s1, out=t1)
            np.subtract(dp, dm, out=t2)
            _shift0(dp, s1, 1)
            np.subtract(s1, dp, out=t3)
            m1 = np.where(t1 * t2 > 0, np.where(np.abs(t1) <= np.abs(t2), t1, t2), 0.0)
            m2 = np.where(t3 * t2 > 0, np.where(np.abs(t3) <= np.abs(t2), t3, t2), 0.0)
            m1 *= 0.5
            np.add(dm, m1, out=dm)
            m2 *= 0.5
            np.subtract(dp, m2, out=dp)
        contrib = np.where(Va > 0, Va * dm, Va * dp)
        if acc is None:
            acc = contrib
        else:
            acc += contrib
    if acc is None:
        return 0.0
    return acc


def main():
    CAND = [('legacy', ufv_legacy), ('rollip', ufv_rollip),
            ('slices', ufv_slices), ('fused', ufv_fused)]
    rng = np.random.default_rng(3)
    phi = rng.standard_normal((N, N, N))
    V = [rng.standard_normal((N, N, N)) * 0.3 for _ in range(AXES)]
    dx = 0.0625

    L = []
    A = L.append
    A('=' * 96)
    A('R577 — upwind_flux_vec 候选微基准（N=%d, %d 次中位）' % (N, REPS))
    A('=' * 96)

    for order in (2, 1):
        A('')
        A('  ---- order=%d ----' % order)
        ref = W.upwind_flux_vec(phi, V, dx, order=order)
        rmax = float(np.max(np.abs(ref))) or 1.0
        for name, fn in CAND:
            got = fn(phi, V, dx, order=order)
            d = float(np.max(np.abs(np.asarray(got) - ref)))
            bit = d == 0.0
            ts = []
            for _ in range(REPS):
                t0 = time.perf_counter()
                fn(phi, V, dx, order=order)
                ts.append(time.perf_counter() - t0)
            A('    %-8s 中位 %8.4f ms   min %8.4f ms   max|Δ|/max = %.3e  %s'
              % (name, statistics.median(ts) * 1e3, min(ts) * 1e3, d / rmax,
                 '✅ 逐位相同' if bit else '⚠ 非逐位'))
            A('             —— %s' % ('（基准）' if name == 'legacy' else ''))

    # ---- 交错配对：legacy vs slices ----
    A('')
    A('  ---- 交错配对（每轮 legacy 与 slices 各一次，取每轮比值）----')
    ratios = []
    for _ in range(REPS):
        ts = {}
        for name, fn in (('legacy', ufv_legacy), ('rollip', ufv_rollip),
                         ('slices', ufv_slices)):
            t0 = time.perf_counter()
            fn(phi, V, dx, order=2)
            ts[name] = time.perf_counter() - t0
        ratios.append((ts['legacy'] / ts['rollip'], ts['legacy'] / ts['slices']))
    A('    legacy/rollip 每轮 = %s' % ['%.3f' % x[0] for x in ratios])
    A('    legacy/slices 每轮 = %s' % ['%.3f' % x[1] for x in ratios])
    A('    **中位 legacy/rollip = %.3fx**  **中位 legacy/slices = %.3fx**'
      % (statistics.median([x[0] for x in ratios]),
         statistics.median([x[1] for x in ratios])))

    # ---- 逐位判据 ----
    A('')
    ref2 = W.upwind_flux_vec(phi, V, dx, order=2)
    ok = True
    for nm, fn in (('rollip', ufv_rollip), ('slices', ufv_slices)):
        d = float(np.max(np.abs(fn(phi, V, dx, order=2) - ref2)))
        A('  判据：`%s` vs legacy 的 max|Δ| = **%.3e**  ⇒ %s'
          % (nm, d, '✅ 逐位相同（可上线）' if d == 0.0 else '❌ 必须修'))
        ok = ok and d == 0.0
    # 负对照：必须能看见差异
    neg = ref2.copy()
    neg[0, 0, 0] += 1e-15
    dn = float(np.max(np.abs(neg - ref2)))
    A('  负对照（把结果扰动 1e-15）：max|Δ| = %.3e ⇒ %s'
      % (dn, '✅ 量具能看见' if dn > 0 else '❌ 量具没有分辨力'))
    ok = ok and dn > 0
    A('')
    A('  === RESULT: %s ===' % ('PASS' if ok else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r577_ufvbench.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
