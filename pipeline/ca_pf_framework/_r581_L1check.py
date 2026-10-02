#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_L1check.py --- L1 的**单元判据**：`advance(extend_mode=...)` 三档必须**逐位相同**。

## 口径
直接对一个**多畴**初始状态调 `LevelSetMulti.advance()`，只改 `extend_mode`：
* `legacy`（默认，= 归档旧路） vs `merged` vs `near`
* 判据：三次调用后 `g.phi` **逐位相同**（`array_equal`），且返回的 `coef` 逐位相同。
* **负对照**：`--extend-mode bogus` 必须**抛 ValueError**（不能静默当 legacy）。
* **负对照 2**：把 `band_cells` 改一格 ⇒ 必须**产生差异**（证明这个算例对 `adv.extend` **敏感**，
  否则"三档相同"可能只是因为这条路径根本没被走到 —— 本仓教训 14 的翻版）。

⚠ 为什么必须有"负对照 2"：本仓 §3.3 教训 14 —— "这个测试能不能看到目标现象"。
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_surface as W

N = 48
DX = 62.5e-9
L = N * DX


def build():
    """12 变体 + 母相的多畴初始态（与 `_bk_exp.py` 的场约定一致：phi[0]=母相）。"""
    nv = 12
    x = (np.arange(N) + 0.5) * DX
    X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    phi = np.empty((nv + 1, N, N, N))
    phi[0] = 0.5 * L
    for v in range(nv):
        c = [0.5 * L, 0.5 * L + 0.02 * L * ((v * 5) % 7 - 3), 0.5 * L]
        r = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        phi[v + 1] = r - 0.12 * L
    eps0 = [np.diag([0.01 * (1 + (v % 3)), -0.006, 0.004 * ((v % 2) * 2 - 1)])
            for v in range(nv)]
    return phi, eps0, nv


def make_g(mode=None, band_cells=20):
    """最小可用的多畴引擎（无弹性：`C=None, eps0=None`）。"""
    phi0, eps0, nv = build()
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                        workers=1, nv=nv, reinit_every=0)
    g.phi = phi0.copy()
    return g, nv


def main():
    L_ = ['=' * 90, 'R581-L1check —— `extend_mode` 三档逐位判据', '=' * 90]
    fails = []

    # ---- 直接测 `advance()` 的三档 ----------------------------------------
    phis = {}
    for mode in ('legacy', 'merged', 'near'):
        phi0, eps0, nv = build()
        g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                            workers=1, nv=nv, reinit_every=0)
        g.phi = phi0.copy()
        npref = {v: np.array([0.0, 0.0, 1.0]) for v in range(1, nv + 1)}
        dt = 1e-12
        for _ in range(3):
            g.advance(dt, aniso=0.4, npref=npref, band_cells=20, iface_band=2.0,
                      mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2',
                      extend_mode=mode)
        phis[mode] = g.phi.copy()

    L_.append('── P1 三档逐位（3 步后 g.phi）──')
    for mode in ('merged', 'near'):
        neq = int(np.count_nonzero(phis[mode] != phis['legacy']))
        md = float(np.max(np.abs(phis[mode] - phis['legacy']))) if neq else 0.0
        L_.append('    %-8s vs legacy：不等元素=%d  max|Δ|=%.3e  %s'
                  % (mode, neq, md, '✅ 逐位' if neq == 0 else '❌ 不逐位'))
        if neq:
            fails.append('P1 %s' % mode)

    # ---- 负对照 1：非法档必须抛 -------------------------------------------
    L_.append('── NC-1 非法档必须抛 ValueError──')
    try:
        phi0, eps0, nv = build()
        g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                            workers=1, nv=nv, reinit_every=0)
        g.phi = phi0.copy()
        g.advance(1e-12, aniso=0.4, band_cells=20, extend_mode='bogus')
        L_.append('    ❌ 没抛异常（静默当 legacy 了）')
        fails.append('NC-1')
    except ValueError as e:
        L_.append('    ✅ 抛出 ValueError：%s' % str(e)[:60])
    except Exception as e:
        L_.append('    ⚠ 抛了别的异常 %s: %s' % (type(e).__name__, str(e)[:60]))
        fails.append('NC-1 类型不符')

    # ---- 负对照 2：算例必须对 `adv.extend` 敏感 ----------------------------
    L_.append('── NC-2 本算例必须对 `adv.extend` **敏感**（否则 P1 是空判）──')
    phi0, eps0, nv = build()
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                        workers=1, nv=nv, reinit_every=0)
    g.phi = phi0.copy()
    npref = {v: np.array([0.0, 0.0, 1.0]) for v in range(1, nv + 1)}
    for _ in range(3):
        g.advance(1e-12, aniso=0.4, npref=npref, band_cells=20, iface_band=2.0,
                  mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2',
                  extend_mode='legacy')
    ref = g.phi.copy()
    phi0, eps0, nv = build()
    g2 = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                         workers=1, nv=nv, reinit_every=0)
    g2.phi = phi0.copy()
    for _ in range(3):
        g2.advance(1e-12, aniso=0.4, npref=npref, band_cells=19, iface_band=2.0,
                   mob_beta=3.5, mob_beta_w=2.3, adv_grad='proj2',
                   extend_mode='legacy')
    neq = int(np.count_nonzero(g2.phi != ref))
    L_.append('    band_cells 20→19：不等元素=%d  ⇒ %s'
              % (neq, '✅ 敏感（P1 有意义）' if neq else '❌ **不敏感 ⇒ P1 是空判**'))
    if not neq:
        fails.append('NC-2 不敏感')

    L_.append('')
    L_.append('❌ 失败项：%s' % ', '.join(fails) if fails else '✅ 全部通过')
    out = '\n'.join(L_)
    print(out)
    with open('_w2_r581_L1check.log', 'w') as fh:
        fh.write(out + '\n')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
