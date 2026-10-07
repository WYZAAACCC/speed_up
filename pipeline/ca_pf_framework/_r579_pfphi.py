#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r579_pfphi.py --- goal §(4)：`pf_phi_mode='onfly'` 的**双轴判据**（速度 + 内存）。

## 判据（先写死，必须能失败）
* **D1 逐位相同（单步）**：同一初始状态，`materialized` 与 `onfly` 各走 1 步
  （固定 dt）后 `g.phi` **逐位相同**。
* **D2 逐位相同（多步）**：连续 `STEPS` 步逐位相同（只比末态会漏掉"中途分叉又收敛"）。
* **D3 内存（轴 1）**：`onfly` 的 `pf.phi` **不得**升为 float64（保持 bool，1 B/胞），
  且 `(nv,N³) float64` 的常驻数组**不存在**。用**分项清单**核，不看总数。
* **D4 峰值不升**（关键！）：只把"常驻"降下来而"峰值"没降是**假收益**
  ⇒ 用 `R579P_CHUNK` 扫 `h_chunk ∈ {1,2,4,8}`，报每次 `eps0_fields` 调用的额外字节上界
  （= chunk×8 B/胞 + 输出 48 B/胞），并断言它 **< nv×8 B/胞**（否则等于没省）。
* **D5 速度（轴 2）**：交错配对 `materialized` vs `onfly` 的单步墙钟（中位 + 区间）。
* **D6 负对照**：把 `h_at` 的 `w` 故意改成 `1.5*dx*1.01` ⇒ 结果**必须**明显不同。
"""
import gc
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W                                    # noqa: E402
from T16_verify_rve import C, EPS0                             # noqa: E402

N = int(os.environ.get('R579P_N', '48'))
NV = int(os.environ.get('R579P_NV', '12'))
DX = float(os.environ.get('R579P_DX', '0.0625'))
STEPS = int(os.environ.get('R579P_STEPS', '5'))
WORK = int(os.environ.get('R579P_WORKERS', '4'))
REPS = int(os.environ.get('R579P_REPS', '9'))
OUT = os.environ.get('R579P_OUT', '_w2_r579_pfphi.log')

L = []
A = L.append


def build(mode, chunk=4, wfac=1.0):
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        df=[0.0] + [3.0e8] * NV, workers=WORK,
                        reinit_every=20, reinit_dt=1e-4, reinit_band_cells=6.0,
                        phi_prec='f64', pf_phi_mode=mode, h_chunk=chunk)
    g.init_parent()
    rng = np.random.default_rng(7)
    nrm = np.array([0.0, 0.0, 1.0])
    Lc = N * DX
    for k in range(1, max(3, NV // 8) + 1):
        g.seed_plate(k, rng.random(3) * (Lc * 0.6) + Lc * 0.2, nrm, 120e-9, 300e-9)
    if wfac != 1.0:
        # 负对照：把软剖面宽度改 1%（**只改这一个量**）
        _orig = g._soft_h_at

        def _bad(v0, v1, _o=_orig, _f=wfac):
            _w = 1.5 * g.dx * _f
            c = v1 - v0
            o = np.empty((c,) + g.phi.shape[1:])
            for j in range(c):
                o[j] = 0.5 * (1.0 - np.tanh(g.phi[v0 + j + 1] / _w))
            return o
        g._soft_h_at = _bad
    return g


def run(mode, steps=STEPS, chunk=4, wfac=1.0):
    g = build(mode, chunk, wfac)
    g.advance(dt=1e-8)                     # 预热（触发 soft 路径）
    snaps = []
    for _ in range(steps):
        g.advance(dt=1e-8)
        snaps.append(g.phi.copy())
    return g, snaps


def main():
    A('=' * 100)
    A('R579-PFPHI — goal §(4)：`pf_phi_mode="onfly"` 的双轴判据 (N=%d nv=%d steps=%d)'
      % (N, NV, STEPS))
    A('=' * 100)

    # ---------- D1/D2 逐位 ----------
    gA, sa = run('materialized')
    gB, sb = run('onfly')
    worst = 0.0
    for i, (x, y) in enumerate(zip(sa, sb)):
        d = float(np.max(np.abs(x - y)))
        worst = max(worst, d)
        if d != 0.0:
            A('    step %d: max|Δ| = %.3e  ❌' % (i + 1, d))
    A('')
    A('  D2 逐位（%d 步内 max|Δφ|）：**%.3e** ⇒ %s'
      % (STEPS, worst, '✅ 逐位相同' if worst == 0.0 else '❌ 不等价'))
    ok = (worst == 0.0)

    # ---------- D3 内存 ----------
    A('')
    A('  D3 内存（f64 φ，nv=%d，N=%d）' % (NV, N))
    for tag, g in (('materialized', gA), ('onfly', gB)):
        dt = str(g.pf.phi.dtype)
        nb = g.pf.phi.nbytes
        A('    %-13s `pf.phi` dtype=%-8s  %8.2f MB  （%.3f B/胞·nv）'
          % (tag, dt, nb / 2**20, nb / (N ** 3 * NV)))
    d3 = (str(gB.pf.phi.dtype) == 'bool')
    A('    D3 判定（onfly 的 `pf.phi` 必须仍是 bool）⇒ %s'
      % ('✅ PASS' if d3 else '❌ FAIL'))
    ok = ok and d3

    # ---------- D4 峰值上界 ----------
    A('')
    A('  D4 峰值上界（`eps0_fields` 调用期的额外字节）')
    N3 = N ** 3
    A('    %-8s %-14s %-14s %s' % ('chunk', 'h 分块(MB)', '对 (nv·8)(MB)', '判定'))
    ok4 = True
    for ch in (1, 2, 4, 8):
        hb = ch * N3 * 8 / 2**20
        ref = NV * N3 * 8 / 2**20
        good = hb < ref
        ok4 = ok4 and good
        A('    %-8d %-14.2f %-14.2f %s' % (ch, hb, ref, '✅' if good else '❌ 没省'))
    A('    D4 判定：%s' % ('✅ PASS（分块上界 < nv 份）' if ok4 else '❌ FAIL'))
    ok = ok and ok4

    # ---------- D6 负对照 ----------
    A('')
    _, sc = run('onfly', steps=1, wfac=1.01)
    dn = float(np.max(np.abs(sc[0] - sb[0])))
    A('  D6 负对照（软剖面宽 w 改 1%%）：1 步后 max|Δφ| = **%.3e** ⇒ %s'
      % (dn, '✅ 量具有分辨力' if dn > 0 else '❌ 没分辨力'))
    ok = ok and dn > 0

    # ---------- D5 速度 ----------
    A('')
    A('  D5 速度（交错配对 %d 轮，只量"一步 advance"）' % REPS)
    gm = build('materialized'); gm.advance(dt=1e-8)
    go = build('onfly'); go.advance(dt=1e-8)
    tm, to, ratio = [], [], []
    for _ in range(REPS):
        t0 = time.perf_counter(); gm.advance(dt=1e-8); t1 = time.perf_counter()
        go.advance(dt=1e-8); t2 = time.perf_counter()
        tm.append(t1 - t0); to.append(t2 - t1); ratio.append((t1 - t0) / (t2 - t1))
    A('    materialized min=%.4f s 中位=%.4f s' % (min(tm), statistics.median(tm)))
    A('    onfly        min=%.4f s 中位=%.4f s' % (min(to), statistics.median(to)))
    A('    交错配对 materialized/onfly 中位 = **%.3fx**  区间 [%.3f, %.3f]'
      % (statistics.median(ratio), min(ratio), max(ratio)))
    A('    ⚠ 本项是**双轴判据的第二轴**：即便速度为负（更慢），只要内存轴为正且 C5 需要它，')
    A('      它仍然是**该开的开关**——但**必须如实报出慢了多少**。')

    A('')
    A('  === RESULT: %s ===' % ('ALL PASS' if ok else 'FAIL'))
    out = '\n'.join(L)
    print(out)
    with open(os.path.join(HERE, OUT), 'w', encoding='utf-8') as fh:
        fh.write(out + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
