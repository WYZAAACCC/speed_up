#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_par.py —— ★★ R1 任务②：Window B 的**共享内存多线程**并行层

为什么需要它（先看实测，不要看推理）
====================================
`_r1_par.py` 在 N=192（24 µm / 125 nm）上的实测（`_w2_r1par_N192.log`）：

  ① **numpy 的逐元素算子确实释放 GIL** —— 把同一个算子按 axis=0 切成 slab、用
     `ThreadPoolExecutor` 跑，wall 时间随线程数**真的下降**。判据是**双对照**：
       * 正对照 `time.sleep`：20 个任务 × 0.05 s → **0.054 s**（真并行 ✓）
       * 负对照 纯 Python 循环：**完全平坦**（GIL 串行 ✓）
     ⇒ 量具本身能分辨"真并行"与"假并行"，所以下面的标度是真的。

  ② 但**加速比有硬天花板**：本机 triad（读2写1）实测
       单线程 **11.08 GB/s** → 多线程饱和 **23.0 GB/s（×2.08）**
     ⇒ **纯流式算子最多 ×2.1**。超过 2.1 的算子（`np.where` ×4.6、
     `winner/runner-up` ×6.8、`np.linalg.norm` ×5.3、`argmin` ×4.1）说明它们
     **不是**带宽受限，而是**延迟/计算受限** —— 那部分能吃到真正的多核。

  ③ `advance` 在 N=192 上 = 34.8 s/步 ≈ **2400 个 DRAM 级"读2写1" pass**
     （反推自实测带宽）。其中 `upwind_flux_vec(order=2)` 一个调用 ≈ 60 个 pass，
     而它被**每个活跃场调用一次**（最多 13 次）⇒ 仅此一项 ≈ 11 s。
     ⇒ **并行化的收益上限由"哪些算子是延迟受限"决定**，不是"有多少核"。

设计（三条硬要求）
==================
  H-1 **逐位相同**：slab 分解必须与单线程结果**逐位相同**，否则不许上线。
      * `np.roll` 系算子（迎风通量、minmod）是**周期** stencil ⇒ slab 的 halo 必须
        **环绕取**（`np.take(mode='wrap')`）。
      * `np.gradient` 是**非周期** stencil（`edge_order=2` 在盒边界用单边差分）
        ⇒ slab 的 halo 必须在**盒边界截断**（不能用环绕，否则边界胞会从单边变中心 ✗）。
      两条都已由 `_r1_par.py` 的 P-4 逐位判据验证。
  H-2 **不改调用点语义**：本模块只提供"与单线程同名同义"的函数；`nthreads<=1`
      或分段过小时**直接走原实现**（零风险回退）。
  H-3 **可诊断**：每次调用累计 wall 时间与分段数，供 `par_report()` 打印；
      不允许"并发静默不生效"（本项目最忌讳的静默失败）。

⚠ 记账（必须与结论一起引用）
  * 本模块**不改变**任何离散格式、不改变求和次序（`einsum`/`argmin`/`norm`
    都在**空间**切片上做，逐胞的归约次序不变）⇒ 结果与单线程**逐位相同**。
  * 线程数**不是**物理参数，只影响 wall 时间 ⇒ 不触发 `MEASUREMENT_SPEC R8`。
  * 真正的上限是 DRAM 带宽（×2.1）。**不要**声称"20 核就能快 20 倍"。
"""
import threading
import time

import numpy as np
from concurrent.futures import ThreadPoolExecutor

__all__ = ['ParCtx', 'edges_of']


def edges_of(n, nth):
    """把 [0,n) 均分成 nth 段（不小于 1 行），返回 nth+1 个边界。"""
    nth = max(1, min(int(nth), int(n)))
    return [int(round(i * n / nth)) for i in range(nth + 1)]


class ParCtx(object):
    """共享内存多线程上下文。**不可跨进程 pickl e**（只在本进程内用）。

    `nthreads=1`（或 None）⇒ 全部算子退化为原单线程实现，行为逐位不变。
    """

    def __init__(self, nthreads=1, min_rows=2):
        self.n = max(1, int(nthreads or 1))
        self.min_rows = max(1, int(min_rows))
        self._ex = None
        self.stats = {}
        # ★ 重入守卫（**死锁防护，必需**）：固定大小的线程池**不能嵌套**使用 ——
        #   若 n 个任务各自再向同一个池提交子任务，池被占满 ⇒ 子任务永远排不上
        #   ⇒ **死锁**。这里的做法是：当前线程已经在并行区内部时，嵌套调用
        #   一律**串行执行**（结果逐位相同，因为所有核都是"切片不变"的）。
        self._tl = threading.local()
        self._nest_max = 0

    def _depth(self):
        return getattr(self._tl, 'depth', 0)

    def _enter(self):
        d = self._depth()
        self._tl.depth = d + 1
        self._nest_max = max(self._nest_max, d + 1)
        return d

    def _leave(self):
        self._tl.depth = max(0, self._depth() - 1)

    # ------------------------------------------------------------ 生命周期
    @property
    def pool(self):
        if self.n <= 1:
            return None
        if self._ex is None:
            self._ex = ThreadPoolExecutor(max_workers=self.n,
                                          thread_name_prefix='wBpar')
        return self._ex

    def set_threads(self, nthreads):
        """运行期改线程数（关掉旧池、下次调用重建）。"""
        n = max(1, int(nthreads or 1))
        if n == self.n:
            return self.n
        self.close()
        self.n = n
        return self.n

    def close(self):
        if self._ex is not None:
            self._ex.shutdown(wait=True)
            self._ex = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ------------------------------------------------------------ 分段工具
    def _segments(self, n0):
        """返回分段数；保证每段 ≥ min_rows 行，否则退化单线程。
           ★ 重入时**必须**返回 1（见 `__init__` 的死锁记账）。"""
        if self.n <= 1 or self._depth() > 0:
            return 1
        nth = min(self.n, max(1, n0 // self.min_rows))
        return nth

    def _bump(self, tag, dt, nth):
        s = self.stats.setdefault(tag, [0.0, 0, 0])
        s[0] += dt
        s[1] += 1
        s[2] = max(s[2], nth)

    def report(self):
        """返回 (总 wall, 逐算子表)。用于证明"并行真的生效了"。"""
        tot = sum(v[0] for v in self.stats.values())
        rows = sorted(self.stats.items(), key=lambda kv: -kv[1][0])
        return tot, rows

    def _wrapped(self, fn, lo, hi):
        """在线程池的 worker 里跑 `fn`，并把该线程标记为"已在并行区内"
           ⇒ 它内部的嵌套调用自动串行（防死锁）。"""
        self._enter()
        try:
            return fn(lo, hi)
        finally:
            self._leave()

    # ------------------------------------------------------------ 核心：空间切片
    def map0(self, fn, n0, axis_out=0, tag='map0'):
        """把 [0,n0) 切成若干段，并行调用 `fn(lo, hi)`；
           `fn` 必须返回**首维 = hi-lo** 的 ndarray。返回拼接后的数组。

           `nthreads<=1` ⇒ 直接 `fn(0, n0)`，**逐位相同**（不做任何拼接）。"""
        nth = self._segments(n0)
        if nth <= 1:
            return fn(0, n0)
        ed = edges_of(n0, nth)
        _t0 = time.perf_counter()
        futs = [self.pool.submit(self._wrapped, fn, ed[i], ed[i + 1])
                for i in range(nth)]
        parts = [f.result() for f in futs]
        out = np.concatenate(parts, axis=axis_out)
        self._bump(tag, time.perf_counter() - _t0, nth)
        return out

    def map0_two(self, fn, n0, tag='map0_two'):
        """同 `map0`，但 `fn` 返回**两个**首维 = hi-lo 的数组。"""
        nth = self._segments(n0)
        if nth <= 1:
            return fn(0, n0)
        ed = edges_of(n0, nth)
        _t0 = time.perf_counter()
        futs = [self.pool.submit(self._wrapped, fn, ed[i], ed[i + 1])
                for i in range(nth)]
        res = [f.result() for f in futs]
        out = (np.concatenate([r[0] for r in res], axis=0),
               np.concatenate([r[1] for r in res], axis=0))
        self._bump(tag, time.perf_counter() - _t0, nth)
        return out

    def for_each(self, items, tag=None):
        """并行执行 `items`（可调用对象列表）。异常**原样抛出**（不许静默吞掉）。"""
        if self.n <= 1 or len(items) <= 1 or self._depth() > 0:
            for it in items:
                it()
            return
        _t0 = time.perf_counter()
        futs = [self.pool.submit(self._call_guarded, it) for it in items]
        err = None
        for f in futs:
            e = f.exception()
            if e is not None and err is None:
                err = e
        if err is not None:
            raise err
        if tag:
            self._bump(tag, time.perf_counter() - _t0, min(self.n, len(items)))

    def _call_guarded(self, it):
        self._enter()
        try:
            return it()
        finally:
            self._leave()

    # ------------------------------------------------------------ 逐胞算子
    def argmin2(self, fields):
        """winner / runner-up（`np.argmin(axis=0)` + 一次掩模扫描）。

           ★ 与 `advance()` 里原来的两段实现**逐位相同**：`np.argmin` 沿 axis=0
             的次序、以及 runner-up 扫描的 j 次序都没有改变，只是在**空间**上切片。"""
        def work(lo, hi):
            sub = fields[:, lo:hi]
            nreg = sub.shape[0]
            k = np.argmin(sub, axis=0)
            l = np.empty(k.shape, dtype=k.dtype)
            best = np.full(k.shape, np.inf)
            for j in range(nreg):
                pj = sub[j]
                mj = (k != j) & (pj < best)
                l[mj] = j
                best[mj] = pj[mj]
            return k, l
        return self.map0_two(work, fields.shape[1], tag='argmin2')

    def argmin(self, fields):
        """`np.argmin(fields, axis=0)` 的空间并行版（= `region()` 的核心）。"""
        return self.map0(lambda lo, hi: np.argmin(fields[:, lo:hi], axis=0),
                         fields.shape[1], tag='argmin(region)')

    def upwind_flux_vec(self, phi, V, dx, order=1):
        """`windowB_surface.upwind_flux_vec` 的并行版（**周期** halo）。

           ⚠ 必须环绕取 halo：`np.roll` 在整盒上是**周期**的，slab 内若不补
             环向 halo，最末一段的 `np.roll` 会拿**自己的开头**当邻居 ✗
             （这正是 `_r1_par.py` 首版 P-4 判 FAIL 的原因 —— 是我探针的 bug，
              不是算子的 bug；修正后逐位相同）。"""
        import windowB_surface as _W
        n0 = phi.shape[0]
        halo = 2 if order >= 2 else 1
        nth = self._segments(n0)
        if nth <= 1:
            return _W.upwind_flux_vec(phi, V, dx, order=order)

        Vv = [np.asarray(v) for v in V]

        def work(lo, hi):
            idx = np.arange(lo - halo, hi + halo) % n0
            sub = phi.take(idx, axis=0)
            Vsub = [(v.take(idx, axis=0) if v.ndim == 3 else v) for v in Vv]
            r = _W.upwind_flux_vec(sub, Vsub, dx, order=order)
            return r[halo:halo + (hi - lo)]
        return self.map0(work, n0, tag='upwind_flux_vec(o%d)' % order)

    def gradient(self, phi, dx, edge_order=2):
        """`np.gradient(phi, dx, edge_order=2)` 的并行版（**盒边界截断** halo）。

           ⚠ 与 `upwind_flux_vec` 相反：`np.gradient` 在**整盒**的首末胞用单边差分，
             slab 里若用环绕 halo，边界胞会变成中心差分 ⇒ **不同** ✗。
             必须把 halo 在盒边界**截断**。"""
        n0 = phi.shape[0]
        nth = self._segments(n0)
        if nth <= 1:
            return np.gradient(phi, dx, edge_order=edge_order)
        ed = edges_of(n0, nth)

        def work(i):
            lo, hi = ed[i], ed[i + 1]
            lo2 = max(0, lo - 1)
            hi2 = min(n0, hi + 1)
            g = np.gradient(phi[lo2:hi2], dx, edge_order=edge_order)
            return [gi[lo - lo2: hi - lo2] for gi in g]
        futs = [self.pool.submit(self._call_guarded, (lambda i=i: work(i)))
                for i in range(nth)]
        _t0 = time.perf_counter()
        res = [f.result() for f in futs]
        out = [np.concatenate([r[a] for r in res], axis=0) for a in range(3)]
        self._bump('gradient', time.perf_counter() - _t0, nth)
        return out

    def upwind_grad2(self, phi, sgn, dx):
        """`windowB_surface.upwind_grad2` 的并行版（**周期** halo=2）。

           ★ 为什么必须环绕：`upwind_grad2` 用 `np.roll`（整盒**周期**）。
             slab 内 `np.roll` 会拿自己的首尾当邻居 ⇒ 最末一段错 ✗。
           ★ 这是 **reinit 的热核**：`sussman_reinit` 迭代 `iters` 次、每次调它一次，
             每次约 90 个全场 pass ⇒ `iters=100` 时单对界面 ≈ 9000 pass。"""
        import windowB_surface as _W
        n0 = phi.shape[0]
        nth = self._segments(n0)
        if nth <= 1:
            return _W.upwind_grad2(phi, sgn, dx)
        halo = 2

        def work(lo, hi):
            idx = np.arange(lo - halo, hi + halo) % n0
            r = _W.upwind_grad2(phi.take(idx, 0), sgn.take(idx, 0), dx)
            return r[halo:halo + (hi - lo)]
        return self.map0(work, n0, tag='upwind_grad2')

    def upwind_grad(self, phi, sgn, dx):
        """`windowB_surface.upwind_grad`（一阶）的并行版（周期 halo=1）。"""
        import windowB_surface as _W
        n0 = phi.shape[0]
        nth = self._segments(n0)
        if nth <= 1:
            return _W.upwind_grad(phi, sgn, dx)
        halo = 1

        def work(lo, hi):
            idx = np.arange(lo - halo, hi + halo) % n0
            r = _W.upwind_grad(phi.take(idx, 0), sgn.take(idx, 0), dx)
            return r[halo:halo + (hi - lo)]
        return self.map0(work, n0, tag='upwind_grad')

    def sussman_reinit(self, phi, dx, iters=40, dtau=None, grad='upwind2',
                       guard=True, band_cells=None):
        """`windowB_surface.sussman_reinit` 的并行版（**与单线程逐位相同**）。

           做法：只有"逐胞算子"并行化（`upwind_grad2` / `np.gradient` / `clip`），
           `max` 归约与标量循环**保持原样** —— 因为 `_dte` 依赖上一步的全局
           `max(gm)`，那是**串行依赖**，并行化会改变数值（不是"同一次归约换次序"，
           而是换了一个迭代轨迹）⇒ **绝不能改**。"""
        import windowB_surface as _W
        nth = self._segments(phi.shape[0])
        if nth <= 1:
            return _W.sussman_reinit(phi, dx, iters=iters, dtau=dtau, grad=grad,
                                     guard=guard, band_cells=band_cells)
        phi0 = phi.copy()
        _g = self.gradient(phi0, dx, edge_order=2)
        _gn = np.sqrt(sum(_gi ** 2 for _gi in _g))
        _sel = None
        if band_cells is not None:
            _sel = np.abs(phi0) <= float(band_cells) * dx
            if not _sel.any():
                _sel = None
        _gm = float(np.median(_gn if _sel is None else _gn[_sel]))
        if _gm > 1e-12 and abs(_gm - 1.0) > 0.2:
            phi = phi / _gm
            phi0 = phi0 / _gm
        S = phi0 / np.sqrt(phi0 ** 2 + dx ** 2)
        if dtau is None:
            dtau = 0.5 * dx / 3.0
        _phi_raw = phi0.copy()
        _lim0 = float(np.max(np.abs(phi0))) + dx
        for _ in range(int(iters)):
            if grad == 'upwind':
                gm = self.upwind_grad(phi, S, dx)
            elif grad == 'upwind2':
                gm = self.upwind_grad2(phi, S, dx)
            elif grad == 'central':
                g = self.gradient(phi, dx, edge_order=2)
                gm = np.sqrt(sum(gi ** 2 for gi in g))
            else:
                gm = _W.grad_sym(phi, dx)
            _gmax = float(np.max(gm if _sel is None else gm[_sel]))
            _dte = min(dtau, 0.5 * dx / 3.0 / max(_gmax, 1.0))
            _upd = _dte * S * (gm - 1.0)
            phi = phi - np.clip(_upd, -0.5 * dx, 0.5 * dx)
            if guard and float(np.max(np.abs(phi))) > 10.0 * _lim0:
                return _phi_raw
        return phi

    def einsum_ii(self, a, b):
        """`np.einsum('...i,...i->...', a, b)` 的空间并行版（逐胞归约次序不变 ⇒ 逐位相同）。"""
        return self.map0(
            lambda lo, hi: np.einsum('...i,...i->...', a[lo:hi], b[lo:hi]),
            a.shape[0], tag='einsum_ii')

    def norm_last(self, a):
        """`np.linalg.norm(a, axis=-1)` 的空间并行版。"""
        return self.map0(lambda lo, hi: np.linalg.norm(a[lo:hi], axis=-1),
                         a.shape[0], tag='norm_last')

    def where(self, cond, x, y):
        """`np.where(cond, x, y)` 的空间并行版（三个操作数都在 axis=0 上切）。"""
        return self.map0(lambda lo, hi: np.where(cond[lo:hi], x[lo:hi], y[lo:hi]),
                         cond.shape[0], tag='where')


# ------------------------------------------------------------------ 自检
def _selftest(N=64, nthreads=4, seed=0):
    """正/负对照：本模块的每个算子都必须与单线程**逐位相同**。"""
    import windowB_surface as W
    rng = np.random.default_rng(seed)
    phi = rng.standard_normal((N, N, N))
    V = [rng.standard_normal((N, N, N)) for _ in range(3)]
    a3 = np.stack(V, -1)
    fields = np.stack([phi] + [phi * (i + 1.3) for i in range(12)])

    p1 = ParCtx(1)
    pn = ParCtx(nthreads)
    ok = True
    rows = []

    def chk(tag, x, y):
        nonlocal ok
        same = (x.dtype == y.dtype) and np.array_equal(
            np.ascontiguousarray(x).view(np.uint8),
            np.ascontiguousarray(y).view(np.uint8))
        md = 0.0 if same else float(np.max(np.abs(np.asarray(x, float)
                                                  - np.asarray(y, float))))
        ok &= same
        rows.append((tag, same, md))
        return same

    chk('upwind_flux_vec o1', p1.upwind_flux_vec(phi, V, 1e-7, 1),
        pn.upwind_flux_vec(phi, V, 1e-7, 1))
    chk('upwind_flux_vec o2', p1.upwind_flux_vec(phi, V, 1e-7, 2),
        pn.upwind_flux_vec(phi, V, 1e-7, 2))
    chk('np.gradient[0]', p1.gradient(phi, 1e-7)[0], pn.gradient(phi, 1e-7)[0])
    chk('np.gradient[2]', p1.gradient(phi, 1e-7)[2], pn.gradient(phi, 1e-7)[2])
    k1, l1 = p1.argmin2(fields)
    kn, ln = pn.argmin2(fields)
    chk('argmin2.karr', k1, kn)
    chk('argmin2.larr', l1, ln)
    chk('np.argmin(region)', p1.argmin(fields), pn.argmin(fields))
    chk('einsum_ii', p1.einsum_ii(a3, a3), pn.einsum_ii(a3, a3))
    chk('norm_last', p1.norm_last(a3), pn.norm_last(a3))
    chk('where', p1.where(phi > 0, phi, -phi), pn.where(phi > 0, phi, -phi))
    sgn = np.where(phi > 0, 1.0, -1.0)
    chk('upwind_grad', p1.upwind_grad(phi, sgn, 1e-7),
        pn.upwind_grad(phi, sgn, 1e-7))
    chk('upwind_grad2', p1.upwind_grad2(phi, sgn, 1e-7),
        pn.upwind_grad2(phi, sgn, 1e-7))
    # ★ reinit 是最贵的一块（iters=100 × ~90 pass）⇒ 必须逐位相同
    for _it in (5, 20):
        chk('sussman_reinit iters=%d' % _it,
            p1.sussman_reinit(phi.copy(), 1e-7, iters=_it, band_cells=6.0),
            pn.sussman_reinit(phi.copy(), 1e-7, iters=_it, band_cells=6.0))
    chk('sussman_reinit band=None',
        p1.sussman_reinit(phi.copy(), 1e-7, iters=5),
        pn.sussman_reinit(phi.copy(), 1e-7, iters=5))

    print('windowB_par 自检  N=%d  nthreads=%d' % (N, nthreads))
    for tag, same, md in rows:
        print('   %-22s 逐位相同 = %-5s   最大差 %.3e' % (tag, same, md))
    print('   ⇒ %s' % ('★ 全部逐位相同（可安全启用）' if ok else '✗ 有差异，禁止启用'))
    return ok


if __name__ == '__main__':
    import sys
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 64
    nt = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    sys.exit(0 if _selftest(N, nt) else 1)
