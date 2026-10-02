#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L2_epsh.py --- ★ L2/L3 合并靶：`eps0_fields_stream`（`el.epsh` = **47.5% 单步**）候选微基准。

## 靶子的来历（**用生产口径的记账表定的，不是猜的**）
`R581` 在 **N=96 / nv=48 / `--pf-phi onfly`**（= 生产口径）下打了一次全量分块记账：
```
  elastic.pair       1.37430 s   57.00%     ← 最大顶层块
    el.sigma_tensor  1.32620 s   55.00%
      el.epsh        1.14563 s   47.52%     ← ★★ 就是它
        el.fft_fwd   0.02940 s    1.22%
      el.sig.contract 0.13403 s    5.56%
```
⇒ `el.epsh` 里 **1.10 s（46.8% 单步）** 是 `eps0_fields_stream`（**注意：它没有自己的 tag，
所以只能由差值定位** —— 这是记账表的一个缺口，本轮补记）。

## 为什么它慢（**不是算子重，是缓存**）
```python
e = np.zeros((6, N, N, N))                      # 48 B/胞 ⇒ N=96 时 **42 MB**（超过 L3）
for v0 in range(0, nv, chunk):
    h = h_at(v0, v1)                            # (c,N,N,N)，内含 c 次整场 tanh
    for j in range(c):
        for p in range(6):
            e[p] += e0v[v0+j, p] * h[j]         # ★ 288 次「整场 axpy」
```
每次 axpy 触碰 `e[p]`(7 MB) + `h[j]`(7 MB) ⇒ 288 × 14 MB ≈ **4.1 GB/步 DRAM 流量**，
而 `e` 只是累加器 —— 它本可以待在 cache 里。

## 候选（**要求逐位**）
| # | 候选 | 依据 |
|---|---|---|
| S0 | 归档（照抄） | 基准 |
| S1 | ★ **空间分块（末轴 slab）**：`for slab: for v-chunk: h_slab; e_slab += …` | **每个胞沿 v 的累加次序完全不变** ⇒ 逐位；`e_slab` 留在 L2/L3 |
| S2 | 空间分块（首轴 slab） | 布局不同，可能更快/更慢 |
| S3 | S1 + chunk 调到 1（`h` 只留 1 份） | 峰值更低 |
| NC-1 | 每个 chunk 内 **v 倒序** | 必须非零（累加次序敏感） |
| NC-2 | 只算 5 个分量（少一维） | 必须非零 |

## 判据
* **P1 逐位**：`array_equal(out, ref)`（`neq == 0`）。
* **P2 负对照必须非零**；且**退化自检**：`slab=N`（一块）必须与 S0 **逐位相同**。
* **P4 计时**：交错配对、臂序轮换、≥7 轮，报中位与区间。
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_pf3d as P3

REPS = 7
NV = 48
DX = 62.5e-9


# ------------------------------------------------------------------ 基线（照抄）
def s0(e0v, h_at, nv, N, chunk=4):
    e = np.zeros((6, N, N, N))
    for v0 in range(0, nv, int(chunk)):
        v1 = min(v0 + int(chunk), nv)
        h = h_at(v0, v1)
        for j in range(v1 - v0):
            hj = h[j]
            for p in range(6):
                e[p] += e0v[v0 + j, p] * hj
    return e


def s1(e0v, h_at, nv, N, chunk=4, slab=8):
    """★ 空间分块（末轴 slab）：`e_slab` 留在 cache 里；每胞沿 v 的累加次序不变。"""
    e = np.zeros((6, N, N, N))
    for z0 in range(0, N, slab):
        z1 = min(z0 + slab, N)
        for v0 in range(0, nv, int(chunk)):
            v1 = min(v0 + int(chunk), nv)
            h = h_at(v0, v1, z0, z1)
            for j in range(v1 - v0):
                hj = h[j]
                for p in range(6):
                    e[p, :, :, z0:z1] += e0v[v0 + j, p] * hj
    return e


def s2(e0v, h_at, nv, N, chunk=4, slab=8):
    """空间分块（首轴 slab）。"""
    e = np.zeros((6, N, N, N))
    for x0 in range(0, N, slab):
        x1 = min(x0 + slab, N)
        for v0 in range(0, nv, int(chunk)):
            v1 = min(v0 + int(chunk), nv)
            h = h_at(v0, v1, x0, x1)
            for j in range(v1 - v0):
                hj = h[j]
                for p in range(6):
                    e[p, x0:x1] += e0v[v0 + j, p] * hj
    return e


def s3(e0v, h_at, nv, N, chunk=1, slab=8):
    return s1(e0v, h_at, nv, N, chunk=1, slab=slab)


def nc1(e0v, h_at, nv, N, chunk=4, slab=8):
    """NC-1：每个 chunk 内 v **倒序** ⇒ 累加次序变了 ⇒ 必须非零。"""
    e = np.zeros((6, N, N, N))
    for v0 in range(0, nv, int(chunk)):
        v1 = min(v0 + int(chunk), nv)
        h = h_at(v0, v1)
        for j in range(v1 - v0 - 1, -1, -1):
            hj = h[j]
            for p in range(6):
                e[p] += e0v[v0 + j, p] * hj
    return e


def nc2(e0v, h_at, nv, N, chunk=4, slab=8):
    """NC-2：少算一个分量（p 只到 5）。"""
    e = np.zeros((6, N, N, N))
    for v0 in range(0, nv, int(chunk)):
        v1 = min(v0 + int(chunk), nv)
        h = h_at(v0, v1)
        for j in range(v1 - v0):
            hj = h[j]
            for p in range(5):
                e[p] += e0v[v0 + j, p] * hj
    return e


def make_case(N, nv=NV):
    """造一个**真实形状**的算例：12 变体 × (nv/12)、板条状 SDF、PF3D 的 e0v。"""
    from T16_verify_rve import C, EPS0
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(nv)]
    pf = P3.PF3D(N, N * DX, C, eps, gamma=0.25, w90=1e-9, Lmob=1e-9, workers=1)
    e0v = pf.e0v
    L = N * DX
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    phi = np.empty((nv + 1, N, N, N))
    phi[0] = 0.5 * L
    for v in range(nv):
        zc = (0.25 + 0.5 * ((v * 7) % 12) / 11.0) * L
        yc = (0.30 + 0.4 * ((v * 5) % 7) / 6.0) * L
        t, w, l = 510e-9, 500e-9, 1000e-9
        dz = np.abs(Z - zc) - 0.5 * t
        dy = np.abs(Y - yc) - 0.5 * w
        dx_ = np.abs(X - 0.5 * L) - 0.5 * l
        a = np.maximum(np.maximum(dz, dy), dx_)
        phi[v + 1] = a + np.minimum(np.maximum(np.maximum(dz, dy), dx_), 0.0)
    _w = 1.5 * (L / N)

    def h_at(v0, v1, z0=None, z1=None, ax=3):
        c = v1 - v0
        if z0 is None:                       # 整场（基线 S0 用）
            out = np.empty((c, N, N, N))
            for j in range(c):
                out[j] = 0.5 * (1.0 - np.tanh(phi[v0 + j + 1] / _w))
            return out
        if ax == 3:
            out = np.empty((c, N, N, z1 - z0))
            for j in range(c):
                out[j] = 0.5 * (1.0 - np.tanh(phi[v0 + j + 1][..., z0:z1] / _w))
        else:
            out = np.empty((c, z1 - z0, N, N))
            for j in range(c):
                out[j] = 0.5 * (1.0 - np.tanh(phi[v0 + j + 1][z0:z1] / _w))
        return out

    return e0v, phi, h_at, _w


def main():
    L = ['=' * 100,
         'R581-L2 —— `eps0_fields_stream`（`el.epsh` = 47.5% 生产单步）候选微基准',
         '=' * 100,
         '  ⚠ 靶子由**生产口径记账表**定（N=96/nv=48/onfly），不是猜的。']
    fails = []
    for N in (64, 96):
        e0v, phi, h_at_full, _w = make_case(N)

        def H(v0, v1, z0=None, z1=None):
            return h_at_full(v0, v1, z0, z1, ax=3)

        def H0(v0, v1, z0=None, z1=None):
            return h_at_full(v0, v1, z0, z1, ax=0)
        ref = s0(e0v, H, NV, N)
        L.append('')
        L.append('── N=%d  nv=%d  `e` 常驻 = %.1f MB  `e0v` = %s ──'
                 % (N, NV, 6 * N ** 3 * 8 / 2 ** 20, e0v.shape))

        L.append('  ── P1 逐位 ──')
        for nm, fn in (('S1 slab=8 (末轴)', lambda: s1(e0v, H, NV, N, 4, 8)),
                       ('S1 slab=16', lambda: s1(e0v, H, NV, N, 4, 16)),
                       ('S1 slab=32', lambda: s1(e0v, H, NV, N, 4, 32)),
                       ('S1 slab=N (退化=一块)', lambda: s1(e0v, H, NV, N, 4, N)),
                       ('S2 slab=8 (首轴)', lambda: s2(e0v, H0, NV, N, 4, 8)),
                       ('S3 chunk=1 slab=8', lambda: s3(e0v, H, NV, N, 1, 8))):
            got = fn()
            neq = int(np.count_nonzero(got != ref))
            md = float(np.max(np.abs(got - ref))) if neq else 0.0
            L.append('    %-24s max|Δ|=%.3e  不等=%d  %s'
                     % (nm, md, neq, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
            if neq:
                fails.append('%s@N%d' % (nm, N))

        L.append('  ── P2 负对照（必须非零）──')
        for nm, fn in (('NC-1 chunk 内 v 倒序', lambda: nc1(e0v, H, NV, N)),
                       ('NC-2 少一个分量', lambda: nc2(e0v, H, NV, N))):
            got = fn()
            neq = int(np.count_nonzero(got != ref))
            L.append('    %-24s 不等=%d  %s'
                     % (nm, neq, '✅ 有分辨力' if neq else '❌ **判据失效**'))
            if neq == 0:
                fails.append('%s@N%d 恒 0' % (nm, N))

        arms = [('S0 归档', lambda: s0(e0v, H, NV, N, 4)),
                ('S1 slab=8', lambda: s1(e0v, H, NV, N, 4, 8)),
                ('S1 slab=16', lambda: s1(e0v, H, NV, N, 4, 16)),
                ('S2 slab=8', lambda: s2(e0v, H0, NV, N, 4, 8))]
        ts = {nm: [] for nm, _ in arms}
        for r in range(REPS):
            order = arms[r % len(arms):] + arms[:r % len(arms)]
            for nm, fn in order:
                t0 = time.perf_counter(); fn()
                ts[nm].append(time.perf_counter() - t0)
        tb = sorted(ts['S0 归档'])[REPS // 2]
        L.append('  ── P4 计时（%d 轮，交错、轮换；中位）──' % REPS)
        for nm, _ in arms:
            v = sorted(ts[nm]); m = v[REPS // 2]
            L.append('    %-14s 中位 %7.4f s  区间 [%.4f, %.4f]  提速 **%6.3f×**'
                     % (nm, m, v[0], v[-1], tb / m))
    L.append('')
    L.append('=' * 100)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 判据全部通过（见上逐项）')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L2_epsh.log', 'w').write(out + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
