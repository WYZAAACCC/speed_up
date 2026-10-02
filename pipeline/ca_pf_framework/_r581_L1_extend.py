#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L1_extend.py --- L1 车道：`adv.extend`（**10.98% 墙钟**，单步最大的单项之一）的候选微基准。

## 被测对象
`windowB_surface.py:4618-4682` 的 `adv.extend` 块，pair_kernel=True 分支：
```python
dfield = pha - phb
gdd = np.gradient(dfield, self.dx, edge_order=2)      # ① 一次 np.gradient
gdn = np.sqrt(sum(g**2 for g in gdd)) + 1e-30
iface = (|dfield| <= iface_band*dx*gdn) & (|v_cell| > 0)
band  = |dfield| <= band_cells*dx*gdn
v_ext = extend_along_normal(where(iface, vcanon, 0.0), dfield, dx,
                            iters=int(band_cells/0.4)+6)   # ② 里面**又算一次同一个 gradient**
coef  = where(band, sigma*v_ext, 0.0)
```

## 本脚本要量的候选（**全部要求逐位相同**）
| # | 候选 | 依据 |
|---|---|---|
| G1 | `np.gradient` → `windowB_par._np_gradient_edge2`（**已在本仓验证过逐位**） | `_r579_grad.py` |
| G2 | ★ **复用**：把 ① 算好的 `gdd`/`gdn` 传给 `extend_along_normal`，消掉 ② | 同一个数组、同一个函数、同一个 dx ⇒ **必然逐位** |
| E1 | `extend_along_normal` 里 **`w = S*(g[ax]/gn)` 提到迭代外**（它是**循环不变量**！） | 现在是 56×3=168 次重算，只用 3 次 |
| E2 | E1 + **融合 `where` 与 `/dx`**：`w*where(w>0, v−vm, vp−v)/dx`（逐元素等价 ⇒ 逐位） | 省 1 趟 N³ |
| E3 | E2 + 首轴直接用（去掉 `zeros_like` + 首次 `+=`） | `0.0 + x == x`（IEEE 精确） |
| B1 | ★★ **只在 `band` 的包围盒（外扩 24 胞）上算延拓**，再散点写回 | 迎风特征**朝界面**传播 ⇒ 外扩 ≥ `iters·dtau_fac` 胞后**带内逐位**（见下） |

## 判据（**先写死**）
* **P1 逐位**：每个候选 vs 基线，`max|Δ|` **必须 == 0.0**（用 `np.array_equal` 判，不用 `<=0`）。
* **P2 负对照（必须有分辨力）**：
  - NC-1 语义错（把 `w>0` 写成 `w<0`）⇒ `max|Δ|` 必须 **> 0**；
  - NC-2 纯舍入差（把 `/dx` 提到循环外提公因式）⇒ 必须 **> 0**（**这一条证明判据能看到
    "数学等价但舍入不同"**，即 P1 的"== 0.0"不是恒真）。
* **P3 B1 的正确性口径**：B1 只保证 **`band` 内**逐位（带外 `coef` 反正被 `where` 置 0）⇒
  判据写成"`band` 内 `max|Δ| == 0`"。**先验**：外扩 24 胞。
* **P4 计时**：交错配对、臂顺序轮换、≥7 轮，报**中位与区间**。

## 几何（**代理，必须如实标注**）
本脚本用「3 块板条状 SDF 之差」造 `dfield = φ_k − φ_l`，形状取自生产配置
（`--plate-L 1000 --plate-W 500 --plate-T 510` nm、`dx=62.5 nm`）。
⚠ **这是代理**：真值要在真实路径上由四道门把关。代理只用于**选候选**与**量 bbox 占比**。
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import windowB_par as PAR
from windowB_surface import extend_along_normal          # 基线（**不改它**）

DX_NM = 62.5
PLATE_T = 510.0 / DX_NM          # 厚 8.16 胞
PLATE_W = 500.0 / DX_NM
PLATE_L = 1000.0 / DX_NM
BAND_CELLS = 20                  # `advance()` 默认 `band_cells=20`
IFACE_BAND = 2.0
ITERS = int(BAND_CELLS / 0.4) + 6        # 56


# ---------------------------------------------------------------- 候选实现
def ext_base(v, phi, dx, iters=ITERS, dtau_fac=0.4):
    """**逐字照抄** `windowB_surface.extend_along_normal`（基线，不许改）。"""
    v = v.copy()
    g = np.gradient(phi, dx, edge_order=2)
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = S * (g[ax] / gn)
            dm = (v - np.roll(v, 1, axis=ax)) / dx
            dp = (np.roll(v, -1, axis=ax) - v) / dx
            cov += w * np.where(w > 0, dm, dp)
        v = v - dtau * cov
    return v


def _grad_gn(phi, dx, gpre=None):
    """`g`/`gn` 的取法。`gpre` 非 None ⇒ 复用调用方算好的 `g`（G2），否则自己算。"""
    if gpre is None:
        g = np.gradient(phi, dx, edge_order=2)
    else:
        g = gpre
    gn = np.sqrt(sum(gi ** 2 for gi in g)) + 1e-30
    return g, gn


def ext_E1(v, phi, dx, iters=ITERS, dtau_fac=0.4, gpre=None):
    """E1：`w` 提到迭代外（循环不变量）。"""
    v = v.copy()
    g, gn = _grad_gn(phi, dx, gpre)
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    W = [S * (g[ax] / gn) for ax in range(3)]
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = W[ax]
            dm = (v - np.roll(v, 1, axis=ax)) / dx
            dp = (np.roll(v, -1, axis=ax) - v) / dx
            cov += w * np.where(w > 0, dm, dp)
        v = v - dtau * cov
    return v


def ext_E2(v, phi, dx, iters=ITERS, dtau_fac=0.4, gpre=None):
    """E2：E1 + 融合 `where` 与 `/dx`（逐元素等价 ⇒ 逐位）。"""
    v = v.copy()
    g, gn = _grad_gn(phi, dx, gpre)
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    W = [S * (g[ax] / gn) for ax in range(3)]
    M = [w > 0 for w in W]
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = W[ax]
            vm = np.roll(v, 1, axis=ax)
            vp = np.roll(v, -1, axis=ax)
            cov += w * (np.where(M[ax], v - vm, vp - v) / dx)
        v = v - dtau * cov
    return v


def ext_E3(v, phi, dx, iters=ITERS, dtau_fac=0.4, gpre=None):
    """E3：E2 + 首轴直接用（去掉 zeros_like 和第一次 +=）。"""
    v = v.copy()
    g, gn = _grad_gn(phi, dx, gpre)
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    W = [S * (g[ax] / gn) for ax in range(3)]
    M = [w > 0 for w in W]
    for _ in range(iters):
        cov = None
        for ax in range(3):
            w = W[ax]
            vm = np.roll(v, 1, axis=ax)
            vp = np.roll(v, -1, axis=ax)
            t = w * (np.where(M[ax], v - vm, vp - v) / dx)
            cov = t if cov is None else cov + t
        v = v - dtau * cov
    return v


def ext_NC1(v, phi, dx, iters=ITERS, dtau_fac=0.4, gpre=None):
    """NC-1 负对照：把迎风判据方向写反 ⇒ **必须**有非零差。"""
    v = v.copy()
    g, gn = _grad_gn(phi, dx, gpre)
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            w = S * (g[ax] / gn)
            dm = (v - np.roll(v, 1, axis=ax)) / dx
            dp = (np.roll(v, -1, axis=ax) - v) / dx
            cov += w * np.where(w < 0, dm, dp)          # ← 反向
        v = v - dtau * cov
    return v


def ext_NC2(v, phi, dx, iters=ITERS, dtau_fac=0.4, gpre=None):
    """NC-2 负对照：**数学等价但舍入不同**（把 1/dx 提公因式）。
    必须给出**非零**差 —— 否则说明"逐位判据"看不到舍入差，即判据没有分辨力。"""
    v = v.copy()
    g, gn = _grad_gn(phi, dx, gpre)
    S = phi / np.sqrt(phi ** 2 + dx ** 2)
    dtau = dtau_fac * dx
    W = [S * (g[ax] / gn) for ax in range(3)]
    M = [w > 0 for w in W]
    for _ in range(iters):
        cov = np.zeros_like(v)
        for ax in range(3):
            vm = np.roll(v, 1, axis=ax)
            vp = np.roll(v, -1, axis=ax)
            cov += W[ax] * np.where(M[ax], v - vm, vp - v)
        v = v - (dtau / dx) * cov                      # ← 提公因式：舍入路径变了
    return v


# ---------------------------------------------------------------- 几何代理
def make_field(N, seed=0):
    """3 块板条状 SDF 之差，形状取自生产 `--plate-*`。返回 (dfield, vcanon, v_cell)。"""
    L = N * DX_NM
    x = (np.arange(N) + 0.5) * DX_NM
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    def plate(z0, y0):
        # 板：z 方向厚 PLATE_T、y 方向宽 PLATE_W、x 方向长 PLATE_L（居中）
        dz = np.abs(Z - z0) - 0.5 * PLATE_T
        dy = np.abs(Y - y0) - 0.5 * PLATE_W
        dx_ = np.abs(X - 0.5 * L) - 0.5 * PLATE_L
        a = np.maximum(np.maximum(dz, dy), dx_)
        return a + np.minimum(np.maximum(np.maximum(dz, dy), dx_), 0.0)
    pa = plate(0.42 * L, 0.50 * L)
    pb = plate(0.58 * L, 0.50 * L)
    dfield = pa - pb                                   # ≈ 2×有符号距离
    rng = np.random.default_rng(seed)
    vcanon = rng.normal(size=(N, N, N))
    v_cell = rng.normal(size=(N, N, N))
    return dfield, vcanon, v_cell


def build_inputs(N):
    dfield, vcanon, v_cell = make_field(N)
    dx = DX_NM
    gdd = np.gradient(dfield, dx, edge_order=2)
    gdn = np.sqrt(sum(g ** 2 for g in gdd)) + 1e-30
    iface = (np.abs(dfield) <= IFACE_BAND * dx * gdn) & (np.abs(v_cell) > 0)
    band = np.abs(dfield) <= BAND_CELLS * dx * gdn
    v0 = np.where(iface, vcanon, 0.0)
    return dict(dfield=dfield, gdd=gdd, gdn=gdn, iface=iface, band=band,
                v0=v0, sigma=np.sign(v_cell), dx=dx)


def bbox_of(mask, pad, N):
    """周期盒下的"最小包围盒"（用最长连续段近似；周期盒上取补集的空隙最长处切开）。"""
    idx = np.flatnonzero(mask.any(axis=(1, 2)))
    idy = np.flatnonzero(mask.any(axis=(0, 2)))
    idz = np.flatnonzero(mask.any(axis=(0, 1)))
    if len(idx) == 0:
        return None
    def span(v, N):
        # 周期：把最长的 0 段切开
        if len(v) == N:
            return 0, N
        gaps = np.diff(np.concatenate([[v[-1] - N], v, [v[0] + N]]))
        k = int(np.argmax(gaps))
        lo = v[(k + 1) % len(v)]
        hi = v[k % len(v)]
        if hi < lo:
            hi += N
        return lo, hi
    out = []
    for v in (idx, idy, idz):
        lo, hi = span(v, N)
        lo -= pad; hi += pad
        lo = max(0, lo); hi = min(N, hi)
        out.append((int(lo), int(hi)))
    return out


def main():
    L = ['=' * 100,
         'R581-L1 —— `adv.extend` 候选微基准',
         '=' * 100,
         '  被测：`windowB_surface.extend_along_normal`（iters=%d，band_cells=%d）'
         % (ITERS, BAND_CELLS),
         '  几何：**代理**（3 块板条状 SDF 之差，生产尺寸）。真值由四道门在真实路径上把关。',
         '']
    fails = []

    for N in (64, 128):
        inp = build_inputs(N)
        dx = inp['dx']; v0 = inp['v0']; dfield = inp['dfield']
        band = inp['band']; iface = inp['iface']
        L.append('─' * 100)
        L.append('N=%d   N³=%d   iface 占比=%.2f%%   band 占比=%.2f%%'
                 % (N, N ** 3, 100.0 * iface.mean(), 100.0 * band.mean()))
        bb = bbox_of(band, 24, N)
        if bb:
            vol = 1
            for lo, hi in bb:
                vol *= (hi - lo)
            L.append('  band 包围盒（外扩 24 胞）= %s  ⇒ 体积占比 **%.1f%%** '
                     '⇒ B1 的理论上限 ≈ **%.1f×**'
                     % (bb, 100.0 * vol / N ** 3, N ** 3 / max(vol, 1)))
        L.append('')

        # ---- 基线 ----------------------------------------------------------
        base = ext_base(v0, dfield, dx)
        ref_band = base[band]

        # ---- P1 逐位 -------------------------------------------------------
        cands = [
            ('E1  w 提出循环', ext_E1, dict()),
            ('E2  E1+融合where/dx', ext_E2, dict()),
            ('E3  E2+首轴直用', ext_E3, dict()),
            ('G2  复用调用方梯度', ext_E3, dict(gpre=inp['gdd'])),
        ]
        L.append('  ── P1 逐位判据（`array_equal`，要求 max|Δ| == 0.0 且无一元素不等）──')
        for name, fn, kw in cands:
            got = fn(v0, dfield, dx, **kw)
            neq = int(np.count_nonzero(got != base))
            md = float(np.max(np.abs(got - base))) if neq else 0.0
            ok = (neq == 0)
            L.append('    %-22s max|Δ|=%.3e  不等元素=%d  %s'
                     % (name, md, neq, '✅ 逐位' if ok else '❌ 不逐位'))
            if not ok:
                fails.append('%s@N%d' % (name, N))

        # ---- P2 负对照 -----------------------------------------------------
        L.append('  ── P2 负对照（**必须非零**，否则判据没有分辨力）──')
        for name, fn, must in (('NC-1 迎风方向写反', ext_NC1, '大'),
                               ('NC-2 数学等价但舍入不同', ext_NC2, '小但非零')):
            got = fn(v0, dfield, dx)
            neq = int(np.count_nonzero(got != base))
            md = float(np.max(np.abs(got - base))) if neq else 0.0
            sc = float(np.max(np.abs(base))) or 1.0
            L.append('    %-22s max|Δ|=%.3e (相对 %.2e)  不等元素=%d  %s'
                     % (name, md, md / sc, neq,
                        '✅ 有分辨力' if neq > 0 else '❌ **判据失效**'))
            if neq == 0:
                fails.append('%s@N%d 恒为 0' % (name, N))

        # ---- B1 包围盒版：只要求 band 内逐位 --------------------------------
        if bb:
            (x0, x1), (y0, y1), (z0, z1) = bb
            sl = (slice(x0, x1), slice(y0, y1), slice(z0, z1))
            sub = ext_E3(v0[sl], dfield[sl], dx)
            got = np.zeros_like(base)
            got[sl] = sub
            neq_in = int(np.count_nonzero((got != base)[band]))
            md_in = float(np.max(np.abs(got - base)[band])) if neq_in else 0.0
            neq_all = int(np.count_nonzero(got != base))
            L.append('  ── P3 B1（band 包围盒 + 外扩 24 胞）──')
            L.append('    band 内：max|Δ|=%.3e  不等元素=%d  %s'
                     % (md_in, neq_in, '✅ 逐位' if neq_in == 0 else '❌ 不逐位'))
            L.append('    （全盒：不等元素=%d —— 带外本来就允许不同，`coef` 会被置 0）'
                     % neq_all)
            if neq_in != 0:
                fails.append('B1@N%d band 内不逐位' % N)

        # ---- P4 计时（交错配对、轮换）--------------------------------------
        arms = [('base', ext_base, dict()),
                ('E1', ext_E1, dict()),
                ('E2', ext_E2, dict()),
                ('E3', ext_E3, dict()),
                ('E3+G2', ext_E3, dict(gpre=inp['gdd']))]
        ts = {k: [] for k, _, _ in arms}
        REPS = 7
        for r in range(REPS):
            order = arms[r % len(arms):] + arms[:r % len(arms)]     # 轮换
            for name, fn, kw in order:
                t0 = time.perf_counter(); fn(v0, dfield, dx, **kw)
                ts[name].append(time.perf_counter() - t0)
        tb = sorted(ts['base'])[REPS // 2]
        L.append('  ── P4 计时（%d 轮，交错、臂序轮换；报中位）──' % REPS)
        for name, _, _ in arms:
            v_ = sorted(ts[name]); med = v_[REPS // 2]
            L.append('    %-8s 中位 %7.4f s   区间 [%.4f, %.4f]   提速 **%.3f×**'
                     % (name, med, v_[0], v_[-1], tb / med))
        L.append('')

    L.append('=' * 100)
    if fails:
        L.append('❌ **有失败项**：%s' % ', '.join(fails))
    else:
        L.append('✅ 全部通过：候选逐位；两个负对照都有分辨力；B1 带内逐位。')
    out = '\n'.join(L)
    print(out)
    with open('_w2_r581_L1_extend.log', 'w') as fh:
        fh.write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
