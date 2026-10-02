#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L2check.py --- L2（`--eps0-tile`）的**真实引擎**逐位判据。

## 为什么不能只信微基准
微基准（`_r581_L2_epsh.py` / `_r581_L2_sweep.py`）用**合成算例**验了 42 档组合逐位。
但本仓的教训（P3）是「**单元量具过 ≠ 真实路径过**」：`eps0_fields` 是**多调用方**函数
（`sigma_tensor` 的 c2c / rfft 两支、`eps0_fields_idx`、诊断 `E_el`），
`_soft_h_at` 的签名也变了 ⇒ 必须在**真引擎**上比。

## 判据
* **P1** `LevelSetMulti(pf_phi_mode='onfly')` 在 `eps0_tile ∈ {0, 2, 4, 8}` 下，
  `sigma_tensor()` 与 `eps0_fields()` 必须**逐位相同**；
* **P2 诊断量**：`E_el()` 也必须逐位相同（P1 的教训：只比 `g.phi` 会漏掉诊断量）；
* **P3 负对照**：`eps0_tile` 指向一个**故意错**的实现（chunk 内 v 倒序）必须产生差异
  —— 用一个 monkeypatch 的 `_eps0_fields_stream_tiled` 模拟；
* **P4 退化**：`eps0_tile = N`（一块）必须与 0 **逐位相同**；
* **P5 非法值**：`eps0_tile = -1` 必须抛 `ValueError`；
* **P6 活性**：`onfly` 下 `pf._h_src is not None` 且 `pf._h_slab == eps0_tile`
  （防"开关看起来生效、实则没接上"）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W
import windowB_pf3d as P3

N = 48
NV = 24
DX = 62.5e-9


def build(tile):
    from T16_verify_rve import C, EPS0
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        workers=1, nv=NV, reinit_every=0,
                        pf_phi_mode='onfly', h_chunk=4, eps0_tile=tile)
    Lc = N * DX
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    rng = np.random.default_rng(3)
    g.phi[0] = 0.5 * Lc
    for v in range(NV):
        c = rng.random(3) * Lc * 0.7 + Lc * 0.15
        g.phi[v + 1] = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2
                               + (Z - c[2]) ** 2) - 0.13 * Lc
    return g


def main():
    L = ['=' * 92, 'R581-L2check —— `--eps0-tile` 真引擎逐位判据', '=' * 92]
    fails = []
    ref_sig = ref_e0 = ref_el = None
    for tile in (0, 2, 4, 8, N):
        g = build(tile)
        # ★ 必须走 `_soft_sigma()` —— 是它把 `_h_src` 挂上去的。
        #   第一版漏了两处，都被判据抓到：
        #     ① tile>0 时漏了 ⇒ `_h_src=None` ⇒ 走物化路 ⇒ "逐位"是**空判**（P6 抓到）；
        #     ② tile=0（基准）时也漏了 ⇒ `pf.phi` 全 0 ⇒ **基准自己是 0**
        #        ⇒ 于是"tile>0 全不等"其实是在跟 0 比（P1 抓到，差满 6·N³ 个元素）。
        _ = g._soft_sigma()
        # P6 活性：onfly 档必须真的挂上了钩子，且 slab 与请求一致
        if tile > 0 and (g.pf._h_src is None or int(getattr(g.pf, '_h_slab', -1)) != tile):
            fails.append('P6 tile=%d 未接上' % tile)
            L.append('    ❌ P6 tile=%d：_h_src=%r _h_slab=%r'
                     % (tile, g.pf._h_src, getattr(g.pf, '_h_slab', None)))
        sig = g.pf.sigma_tensor(None)
        e0 = g.pf.eps0_fields()
        el = g.pf.E_el()
        if tile == 0:
            ref_sig, ref_e0, ref_el = sig, e0, el
            L.append('    基准 tile=0 ： sigma 逐位自检 ✅   E_el=%.17g' % el)
            continue
        ns = int(np.count_nonzero(sig != ref_sig))
        ne = int(np.count_nonzero(e0 != ref_e0))
        dl = abs(el - ref_el)
        L.append('    tile=%-3d sigma 不等=%-8d eps0 不等=%-8d  |ΔE_el|=%.3e  %s'
                 % (tile, ns, ne, dl,
                    '✅ 逐位' if (ns == 0 and ne == 0 and dl == 0.0) else '❌ 有差异'))
        if ns or ne or dl != 0.0:
            fails.append('P1/P2 tile=%d' % tile)

    # ---- P3 负对照：故意错的 tiled 实现必须产生差异 ------------------------
    L.append('')
    L.append('  ── P3 负对照：把 `_eps0_fields_stream_tiled` 换成"chunk 内 v 倒序" ──')
    orig = P3.PF3D._eps0_fields_stream_tiled

    def wrong(self, h_at, chunk, slab):
        Nn = self.N
        e = np.zeros((6, Nn, Nn, Nn))
        e0v = self.e0v
        for x0 in range(0, Nn, slab):
            x1 = min(x0 + slab, Nn)
            for v0 in range(0, self.nv, int(chunk)):
                v1 = min(v0 + int(chunk), self.nv)
                h = h_at(v0, v1, x0, x1)
                for j in range(v1 - v0 - 1, -1, -1):        # ← 倒序
                    hj = h[j]
                    for p in range(6):
                        e[p, x0:x1] += e0v[v0 + j, p] * hj
        return e
    P3.PF3D._eps0_fields_stream_tiled = wrong
    try:
        g = build(4)
        _ = g._soft_sigma()                 # ★ 同样必须走 `_soft_sigma()`
        sig = g.pf.sigma_tensor(None)
        neq = int(np.count_nonzero(sig != ref_sig))
        L.append('    不等元素=%d  %s' % (neq, '✅ 有分辨力' if neq else '❌ **判据失效**'))
        if not neq:
            fails.append('P3 负对照恒 0')
    finally:
        P3.PF3D._eps0_fields_stream_tiled = orig

    # ---- P5 非法值 ---------------------------------------------------------
    L.append('')
    L.append('  ── P5 非法 `eps0_tile=-1` 必须抛 ValueError ──')
    try:
        build(-1)
        L.append('    ❌ 没抛')
        fails.append('P5')
    except ValueError as e:
        L.append('    ✅ %s' % str(e)[:70])

    L.append('')
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L2check.log', 'w').write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
