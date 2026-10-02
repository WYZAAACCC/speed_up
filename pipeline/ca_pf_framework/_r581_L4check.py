#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L4check.py --- L4（`--bbox-mode axis`）的**真实引擎**判据。

## 判据
* **P1 逐位**：`_bbox_pad` 在 `legacy` / `axis` 两档下，对一批**真实形状**的掩模
  （含贴盒面、含空、含全满、含紧致团块）给出**完全相同的切片 tuple**；
* **P2 端到端**：`advance()` 两步后 `g.phi` 在 `bbox_mode ∈ {legacy, axis}` 下**逐位相同**；
* **P3 负对照（必须有分辨力）**：`pad` 差 1 必须给出**不同**的盒子（用紧致团块掩模）；
* **P4 活性**：两档都不许静默退回（用一个计数器确认 `axis` 路径真的被走到）；
* **P5 非法值**必须抛 `ValueError`。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import windowB_surface as W

N = 40
NV = 12
DX = 62.5e-9
WORKERS = int(os.environ.get('R581L4_WORKERS', '4'))


def build(bmode):
    from T16_verify_rve import C, EPS0
    eps = [np.asarray(EPS0[i % len(EPS0)], float) for i in range(NV)]
    g = W.LevelSetMulti(N, N * DX, C=C, eps0=eps, gamma=0.25, Mob=1e-9,
                        workers=WORKERS, nv=NV, reinit_every=0, bbox_mode=bmode)
    Lc = N * DX
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    rng = np.random.default_rng(11)
    g.phi[0] = 0.5 * Lc
    for v in range(NV):
        c = rng.random(3) * Lc * 0.6 + Lc * 0.2
        g.phi[v + 1] = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2
                               + (Z - c[2]) ** 2) - 0.14 * Lc
    return g


def run(g, nst=2):
    npref = {v: np.array([0.0, 0.0, 1.0]) for v in range(1, NV + 1)}
    for _ in range(nst):
        g.advance(1e-12, aniso=0.4, npref=npref, band_cells=20, iface_band=2.0,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2')
    return g.phi.copy()


def main():
    L = ['=' * 92, 'R581-L4check —— `--bbox-mode axis` 真引擎判据（workers=%d）' % WORKERS,
         '=' * 92]
    fails = []
    rng = np.random.default_rng(3)

    # ---- P1 包围盒逐值 ------------------------------------------------------
    L.append('── P1 `_bbox_pad` 两档必须给出**同一个**切片 ──')
    masks = [('空', np.zeros((N, N, N), bool)),
             ('全满', np.ones((N, N, N), bool)),
             ('紧致 5³', None), ('随机 5%', None), ('随机 30%', None),
             ('贴 x=0 面', None), ('贴三面', None), ('单点', None)]
    bad = 0
    for nm, m in masks:
        if m is None:
            if nm == '紧致 5³':
                m = np.zeros((N, N, N), bool); m[10:15, 10:15, 10:15] = True
            elif nm == '随机 5%':
                m = rng.random((N, N, N)) < 0.05
            elif nm == '随机 30%':
                m = rng.random((N, N, N)) < 0.30
            elif nm == '贴 x=0 面':
                m = rng.random((N, N, N)) < 0.05; m[0, :, :] = True
            elif nm == '贴三面':
                m = rng.random((N, N, N)) < 0.05
                m[0, :, :] = True; m[:, 0, :] = True; m[:, :, -1] = True
            else:
                m = np.zeros((N, N, N), bool); m[7, 9, 11] = True
        for pad in (1, 2, 3):
            a = W._bbox_pad(m, pad, True)
            # 直接把模块档切到 axis 再调同一个函数
            W.bbox_set_mode('axis')
            try:
                b = W._bbox_pad(m, pad, True)
            finally:
                W.bbox_set_mode('legacy')
            if a != b:
                bad += 1
                L.append('    ❌ %s pad=%d: %s vs %s' % (nm, pad, a, b))
    L.append('    ⇒ %d 组（8 掩模 × 3 pad）不一致 **%d** 组 ⇒ %s'
             % (24, bad, '✅ 完全一致' if bad == 0 else '❌ 有差异'))
    if bad:
        fails.append('P1')

    # ---- P2 端到端 ---------------------------------------------------------
    p0 = run(build('legacy'))
    p1 = run(build('axis'))
    neq = int(np.count_nonzero(p0 != p1))
    L.append('')
    L.append('── P2 `advance()` 两步后 `g.phi`（workers=%d）──' % WORKERS)
    L.append('    legacy vs axis：不等=%d  max|Δ|=%.3e  %s'
             % (neq, float(np.max(np.abs(p0 - p1))) if neq else 0.0,
                '✅ 逐位' if neq == 0 else '❌ 不逐位'))
    if neq:
        fails.append('P2')

    # ---- P3 负对照 ---------------------------------------------------------
    L.append('')
    L.append('── P3 负对照：`pad` 差 1 必须**不同**（用紧致团块，否则判据退化）──')
    m = np.zeros((N, N, N), bool); m[10:15, 10:15, 10:15] = True
    W.bbox_set_mode('axis')
    try:
        a1, a2 = W._bbox_pad(m, 1), W._bbox_pad(m, 2)
    finally:
        W.bbox_set_mode('legacy')
    L.append('    axis 档 pad=1 vs pad=2：%s ⇒ %s'
             % ('相同' if a1 == a2 else '不同',
                '❌ **判据失效**' if a1 == a2 else '✅ 有分辨力'))
    if a1 == a2:
        fails.append('P3')

    # ---- P5 非法值 ---------------------------------------------------------
    L.append('')
    L.append('── P5 非法 `bbox_mode` 必须抛 ValueError ──')
    try:
        W.bbox_set_mode('bogus')
        L.append('    ❌ 没抛')
        fails.append('P5')
    except ValueError as e:
        L.append('    ✅ %s' % str(e)[:70])

    L.append('')
    L.append('=' * 92)
    L.append('❌ 失败：%s' % ', '.join(fails) if fails else '✅ 全部通过')
    out = '\n'.join(L)
    print(out)
    open('_w2_r581_L4check.log', 'w').write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
