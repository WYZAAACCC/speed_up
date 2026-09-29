#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_prof_line.py --- R30 审计 S1：`LevelSetMulti.advance()` 的**逐行实测**耗时。

只读审计工具：**不修改**任何已有文件。它只在**内存里**用 `sys.settrace` 给
`windowB_surface.py` / `windowB_par.py` / `windowB_lath.py` 的每一行 Python
打时间戳（行内调用的 numpy/scipy 是 C，不产生 trace 事件 ⇒ 时间算在该行上）。

统计口径
--------
* `incl` = 行内时间（含该行调用的**已跟踪子帧**）
* `excl` = `incl` 减去该行调用的**已跟踪子帧**的时间（worker 线程不被跟踪，
  因此并行算子的时间留在父行的 excl 里 —— 这正是我们要的"算子总代价"）
* 线程数 >1 时 worker 线程不在 `sys.settrace` 覆盖范围内（那是 `threading.settrace`），
  所以**逐行表只在 workers=1 下有意义**。

用法（WSL）：
  /root/miniconda3/envs/ml/bin/python -u _r30_prof_line.py <N> <workers> <nsample>
默认 N=96 workers=1 nsample=2。
"""
import json
import os
import sys
import time

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
import windowB_lath as WL                                       # noqa: E402
from T16_verify_rve import C, EPS0, NPF, DF, MOB                # noqa: E402

ARGS = [a for a in sys.argv[1:]]
N = int(ARGS[0]) if len(ARGS) > 0 else 96
NW = int(ARGS[1]) if len(ARGS) > 1 else 1
NS = int(ARGS[2]) if len(ARGS) > 2 else 2
DX = 125e-9
GAMMA0 = 0.25
BETA_H = 3.5
BETA_W = 2.3
NLATH = 11
TRACE_PREFIX = ('windowB_surface.py', 'windowB_par.py', 'windowB_lath.py',
                'windowB_film.py')


# ===================================================================== 量具
class LineProf(object):
    def __init__(self, prefixes):
        self.prefixes = tuple(os.path.join(_HERE, p) for p in prefixes) + \
            tuple(prefixes)
        self.excl = {}
        self.incl = {}
        self.cnt = {}
        self.frames = {}
        self.ncall = 0

    def trace(self, frame, event, arg):
        self.ncall += 1
        if frame.f_code.co_filename.endswith(TRACE_PREFIX) or \
                frame.f_code.co_filename.startswith(self.prefixes):
            return self.local_trace
        return None

    def local_trace(self, frame, event, arg):
        if event == 'exception':
            return self.local_trace
        now = time.perf_counter()
        st = self.frames.get(frame)
        if st is not None:
            key, t0 = st[0], st[1]
            dt = now - t0
            e = self.excl.get(key)
            if e is None:
                self.excl[key] = [0.0]
                self.incl[key] = [0.0]
                self.cnt[key] = [0]
                e = self.excl[key]
            e[0] += dt - st[2]
            self.incl[key][0] += dt
            self.cnt[key][0] += 1
            st[2] = 0.0
        if event == 'return':
            tot = now - st[3] if st is not None else 0.0
            self.frames.pop(frame, None)
            p = frame.f_back
            if p is not None and p in self.frames:
                ps = self.frames[p]
                ps[2] += tot
            return None
        co = frame.f_code
        key = (co.co_filename, co.co_name, frame.f_lineno)
        if st is None:
            self.frames[frame] = [key, now, 0.0, now]
        else:
            st[0] = key
            st[1] = now
        return self.local_trace

    def top(self, n=60):
        rows = sorted(self.excl.items(), key=lambda kv: -kv[1][0])[:n]
        out = []
        for (fn, func, ln), v in rows:
            out.append((os.path.basename(fn), func, ln, v[0],
                        self.incl[(fn, func, ln)][0], self.cnt[(fn, func, ln)][0]))
        return out

    def by_func(self):
        agg = {}
        for (fn, func, ln), v in self.excl.items():
            k = (os.path.basename(fn), func)
            a = agg.setdefault(k, [0.0, 0.0, 0])
            a[0] += v[0]
            a[1] += self.incl[(fn, func, ln)][0]
            a[2] += self.cnt[(fn, func, ln)][0]
        return sorted(agg.items(), key=lambda kv: -kv[1][0])


# ===================================================================== 装置
def build(N, NW):
    L = N * DX
    laths = [1] * NLATH
    lt = WL.LathTable(laths, omegas=WL.default_omega(len(laths), 5.0),
                      eps0_var=EPS0, npref_var=NPF, gamma0=GAMMA0)
    eps0 = [np.asarray(lt.eps0[i], float) for i in range(len(laths))]
    npref = {i + 1: np.asarray(lt.npref[i + 1], float)
             for i in range(len(laths))}
    nv = len(eps0)
    t0 = time.time()
    g = W.LevelSetMulti(N, L, C=C, eps0=eps0, gamma=GAMMA0, Mob=MOB,
                        df=[0.0] + [DF] * nv, workers=NW, reinit_every=0,
                        reinit_dt=1.0e-4, reinit_band_cells=6.0)
    g.lath = lt
    t_build = time.time() - t0
    c0 = np.array([L / 2] * 3)
    n_hab = np.asarray(NPF[1], float)
    n_hab /= np.linalg.norm(n_hab)
    w_ax = np.asarray(g.wtab[1], float)
    w_ax /= np.linalg.norm(w_ax)
    a_ax = np.asarray(g.atab[1], float)
    a_ax /= np.linalg.norm(a_ax)
    # 与生产 `_bk_closed --tag cln11` 同量级：厚 635 nm、宽 1224 nm、长 4590 nm
    # `R30_PLATE_DX=1` ⇒ 按胞数给（小盒冒烟测试用），默认按生产的物理尺寸。
    if os.environ.get('R30_PLATE_DX') == '1':
        T, gap, Wd, Lp = 3 * DX, 0.0, 6 * DX, 12 * DX
    else:
        T, gap, Wd, Lp = 635e-9, 0.0, 1224e-9, 4590e-9
    for i in range(nv):
        off = (i - (nv - 1) / 2.0) * (T + gap)
        g.seed_plate(i + 1, c0 + off * n_hab, n_hab, Wd / 2, T,
                     elong=Lp / Wd, along=a_ax, flat_end=True)
    g.init_parent()
    return g, npref, n_hab, w_ax, a_ax, t_build


def main():
    print('=' * 104)
    print('_r30_prof_line   N=%d  Δx=%.1f nm  L=%.3f µm  nreg=%d  workers=%d'
          % (N, DX * 1e9, N * DX * 1e6, NLATH + 1, NW))
    print('=' * 104, flush=True)
    g, npref, n_hab, w_ax, a_ax, t_build = build(N, NW)
    print('构造（含 %d 个 argmin_normal + ncmp）耗时 %.1f s' % (NLATH, t_build))
    reg = g.region()
    act = np.unique(reg)
    print('活跃区域 = %s（共 %d/%d）' % (act.tolist(), act.size, g.nreg))
    print('n*=%s  w=%s  a=%s  (n*·a=%.4f)'
          % (np.array2string(n_hab, precision=4),
             np.array2string(w_ax, precision=4),
             np.array2string(a_ax, precision=4), float(n_hab @ a_ax)))
    dx = g.dx
    dt = 0.15 * dx / (MOB * DF)
    kw = dict(aniso=0.4, npref=npref, band_cells=20, mob_beta=BETA_H,
              mob_beta_w=BETA_W, adv_grad='proj2', norm_smooth=0,
              facet_lam=0.0, facet_eps=0.05)
    print('dt = %.4e s（标称 %.2f nm/步）' % (dt, 0.15 * dx * 1e9))
    print('advance kwargs = %s' % {k: v for k, v in kw.items()
                                   if k != 'npref'}, flush=True)

    # ---------------- 1) 无跟踪：基准 wall ----------------
    g.advance(dt, **kw)                       # 预热
    t0 = time.perf_counter()
    for _ in range(NS):
        g.advance(dt, **kw)
    wall = (time.perf_counter() - t0) / NS
    print('\n[1] 无跟踪基准：advance = **%.3f s/步**（%d 步平均）' % (wall, NS))
    tot, rows = g.par.report()
    print('    并行算子累计 wall = %.3f s；逐算子（tag, 累计秒, 次数, 最大分段）:'
          % tot)
    for tag, s in rows:
        print('      %-28s %8.3f s  n=%-6d nth_max=%d' % (tag, s[0], s[1], s[2]))

    # ---------------- 2) 逐行跟踪（1 步，同一对象、紧随其后） ----------------
    g2 = g
    pr = LineProf(TRACE_PREFIX)
    sys.settrace(pr.trace)
    t0 = time.perf_counter()
    try:
        g2.advance(dt, **kw)
    finally:
        sys.settrace(None)
    wall_tr = time.perf_counter() - t0
    print('\n[2] 逐行跟踪 1 步：wall = %.3f s（跟踪开销 ×%.2f；'
          '下面的占比按**跟踪内的 excl** 归一）' % (wall_tr, wall_tr / wall))
    print('    跟踪期全局 call 事件数 = %d' % pr.ncall)

    print('\n' + '=' * 104)
    print('逐行 excl 前 60（file / func:line / excl_s / incl_s / hits）')
    print('=' * 104)
    for fn, func, ln, ex, inc, c in pr.top(60):
        print('  %-20s %-22s %5d  %8.4f  %8.4f  %6d'
              % (fn, func, ln, ex, inc, c))

    print('\n' + '=' * 104)
    print('按函数聚合（excl / incl / 行命中数）')
    print('=' * 104)
    for (fn, func), a in pr.by_func():
        print('  %-20s %-24s excl=%8.4f  incl=%8.4f  hits=%d'
              % (fn, func, a[0], a[1], a[2]))

    dump = dict(
        N=N, dx=DX, workers=NW, nreg=int(g.nreg), n_active=int(act.size),
        dt=dt, wall_untraced=wall, wall_traced=wall_tr, nsample=NS,
        kwargs=dict(aniso=0.4, band_cells=20, mob_beta=BETA_H,
                    mob_beta_w=BETA_W, adv_grad='proj2', norm_smooth=0,
                    facet_lam=0.0, facet_eps=0.05),
        par_stats={k: v for k, v in rows},
        par_total=tot,
        lines=[dict(file=fn, func=func, line=ln, excl=ex, incl=inc, hits=c)
               for fn, func, ln, ex, inc, c in pr.top(400)],
        funcs=[dict(file=fn, func=func, excl=a[0], incl=a[1], hits=a[2])
               for (fn, func), a in pr.by_func()],
    )
    tag = 'N%d_w%d' % (N, NW)
    with open(os.path.join(_HERE, '_r30_prof_line_%s.json' % tag), 'w') as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print('\n→ 原始数据写入 _r30_prof_line_%s.json' % tag)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
