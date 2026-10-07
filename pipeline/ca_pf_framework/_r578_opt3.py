#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r578_opt3.py --- goal §(3)① 与 ③ 的**候选微基准 + 逐位判据**（先量后改）。

* **①** `argmin2` 的 runner-up 扫描：
    现写法 `l[mj] = j` / `best[mj] = pj[mj]`（**布尔花式索引** ⇒ 每次要走
    `np.nonzero` 造索引数组）；候选 `np.copyto(l, j, where=mj)` / `np.copyto(best, pj, where=mj)`
    —— 语义等价，但**不造索引数组**。
* **③** `act = np.unique(np.concatenate((np.unique(karr), np.unique(larr))))`
    （**三次 O(N³ log N) 排序**）→ `np.flatnonzero(np.bincount(karr.ravel(), minlength=nreg)
    + np.bincount(larr.ravel(), minlength=nreg))`（线性计数）。

判据：候选与旧写法**逐位相同**才算通过；负对照必须能看见差异。
"""
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

N = int(os.environ.get('R578_N3', '64'))
NREG = int(os.environ.get('R578_NREG', '25'))
REPS = int(os.environ.get('R578_REPS', '9'))


# ------------------------------------------------------------------ ① runner-up
def argmin2_legacy(fields):
    k = np.argmin(fields, axis=0)
    l = np.empty(k.shape, dtype=k.dtype)
    best = np.full(k.shape, np.inf)
    for j in range(fields.shape[0]):
        pj = fields[j]
        mj = (k != j) & (pj < best)
        l[mj] = j
        best[mj] = pj[mj]
    return k, l


def argmin2_copyto(fields):
    k = np.argmin(fields, axis=0)
    l = np.empty(k.shape, dtype=k.dtype)
    best = np.full(k.shape, np.inf)
    for j in range(fields.shape[0]):
        pj = fields[j]
        mj = (k != j) & (pj < best)
        np.copyto(l, j, where=mj)
        np.copyto(best, pj, where=mj)
    return k, l


# ------------------------------------------------------------------ ③ act
def act_unique(karr, larr, nreg):
    return np.unique(np.concatenate((np.unique(karr), np.unique(larr))))


def act_bincount(karr, larr, nreg):
    c = np.bincount(karr.ravel(), minlength=nreg)
    c += np.bincount(larr.ravel(), minlength=nreg)
    return np.flatnonzero(c)


def _bench(fn, *a, reps=REPS):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn(*a)
        ts.append(time.perf_counter() - t0)
    return min(ts), statistics.median(ts)


def _paired(fa, fb, *a, reps=REPS):
    r = []
    for _ in range(reps):
        t0 = time.perf_counter(); fa(*a); ta = time.perf_counter() - t0
        t0 = time.perf_counter(); fb(*a); tb = time.perf_counter() - t0
        r.append(ta / tb)
    return r


def main():
    rng = np.random.default_rng(11)
    # 造一个"像真的" argmin2 输入：nreg 个场，其中一个明显更小（winner 偏 0）
    fields = rng.random((NREG, N, N, N)).astype(np.float64)
    fields[0] -= 0.5
    # karr/larr：只有 4 个场活跃（与生产实测的 nact=4/nreg=25 同构）
    karr = np.zeros((N, N, N), dtype=np.intp)
    larr = np.ones((N, N, N), dtype=np.intp)
    live = rng.random((N, N, N)) < 0.15
    karr[live] = rng.integers(0, 4, size=int(live.sum()))
    larr[live] = rng.integers(0, 4, size=int(live.sum()))

    L = []
    A = L.append
    A('=' * 96)
    A('R578 — goal §(3)①/③ 候选微基准（N=%d nreg=%d, %d 轮取 min）' % (N, NREG, REPS))
    A('=' * 96)

    # ---- ① ----
    A('')
    A('  ---- ① argmin2 的 runner-up 扫描 ----')
    k0, l0 = argmin2_legacy(fields)
    k1, l1 = argmin2_copyto(fields)
    dk = int(np.max(np.abs(k0 - k1)))
    dl = int(np.max(np.abs(l0 - l1)))
    ta, _ = _bench(argmin2_legacy, fields)
    tb, _ = _bench(argmin2_copyto, fields)
    r = _paired(argmin2_legacy, argmin2_copyto, fields)
    A('    legacy   min=%.4f s    copyto  min=%.4f s' % (ta, tb))
    A('    逐位：max|Δk| = %d, max|Δl| = %d  ⇒ %s'
      % (dk, dl, '✅ 逐位相同' if (dk == 0 and dl == 0) else '❌ 不等价'))
    A('    交错配对 legacy/copyto 中位 = **%.3fx**  区间 [%.3f, %.3f]'
      % (statistics.median(r), min(r), max(r)))

    # ---- ③ ----
    A('')
    A('  ---- ③ act = unique(∪) vs bincount ----')
    a0 = act_unique(karr, larr, NREG)
    a1 = act_bincount(karr, larr, NREG)
    same = (a0.shape == a1.shape) and bool(np.array_equal(a0, a1))
    A('    legacy  act = %s' % a0.tolist())
    A('    bincount act = %s  ⇒ %s'
      % (a1.tolist(), '✅ 同一个升序集合' if same else '❌ 不同'))
    ta2, _ = _bench(act_unique, karr, larr, NREG)
    tb2, _ = _bench(act_bincount, karr, larr, NREG)
    r2 = _paired(act_unique, act_bincount, karr, larr, NREG)
    A('    legacy   min=%.5f s    bincount  min=%.5f s' % (ta2, tb2))
    A('    交错配对 legacy/bincount 中位 = **%.2fx**  区间 [%.2f, %.2f]'
      % (statistics.median(r2), min(r2), max(r2)))

    # ---- 负对照 ----
    A('')
    A('  ---- 负对照（量具必须能看见差异）----')
    kbad = k0.copy(); kbad[0, 0, 0] += 1
    A('    argmin2 扰动 1 个胞 ⇒ max|Δk| = %d  ⇒ %s'
      % (int(np.max(np.abs(kbad - k0))),
         '✅ 能看见' if int(np.max(np.abs(kbad - k0))) > 0 else '❌ 没分辨力'))
    abad = act_bincount(karr, larr, NREG + 7)
    A('    bincount 用 minlength=nreg+7 ⇒ act 长度 %d vs %d  ⇒ %s'
      % (abad.size, a0.size,
         '（口径差异，非错误）' if abad.size >= a0.size else '⚠'))
    A('')
    ok = (dk == 0 and dl == 0 and same)
    A('  === RESULT: %s ===' % ('PASS' if ok else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, '_w2_r578_opt3.log'), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
