#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T12_verify_box.py --- T12 判据（盒子配置与绕盒）的**第一件：D12a 绕盒守卫**。

背景（审计实测）
----------------
`_audit_geom.py`：**9/9** 个单核算例的"长"都 **> L**，占投影上限 `L·Σ|u_i|` 的
**70%–96%**（C1 95.8%、A1 91.9%、N1 89.2%、A0 86.6% …）—— 而那批正是
`EXPERT_REVIEW_RESPONSE.md §5` 当作"第一批干净板条数据"的算例。
⇒ 周期盒绕盒会**静默污染**所有长度/长径比结论。

判据
----
  T12-A1 **正对照**：人为构造**确定绕盒**的构型（区域贯通 x 轴）
          ⇒ `wrap_axes` 必须报出该轴（否则守卫是坏的）
  T12-A2 **负对照**：区域不贯通 ⇒ 不得报（否则守卫会误杀正常算例）
  T12-A3 **硬失败**：`wrap_strict=True` 时 `check_wrap` 必须**抛错**
  T12-A4 **真实场景**：一个小盒 + 长板条（L 只有板条长的 ~1.2 倍）⇒ 守卫必须触发；
          同一个板条放进大盒（L 是板条长的 ~4 倍）⇒ 不得触发

用法：python3 T12_verify_box.py
退出码：0 = PASS
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                     # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)
EPS0, _F, _M = variants()
NV = len(EPS0)
_rng = np.random.default_rng(0)
NPF = {}
for v in range(NV):
    best, bn = None, None
    for n in _rng.normal(size=(400, 3)):
        n = n / np.linalg.norm(n)
        val = 0.5 * float(np.einsum('ij,ijkl,kl->', EPS0[v], _lam_full(C, n), EPS0[v]))
        if best is None or val < best:
            best, bn = val, n
    NPF[v + 1] = bn


def mk(N, dx):
    L = N * dx
    g = W.LevelSetMulti(N, L, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                        df=[0.0, 1e8], workers=1, reinit_every=0, nv=1)
    return g, L


def main():
    print('=' * 100)
    print('T12 —— 绕盒守卫（D12a）')
    print('=' * 100)
    N, dx = 48, 2.5e-8
    g, L = mk(N, dx)

    # --- A1 正对照：区域贯通 x 轴（整条 x 方向通道） ---
    for j in range(g.nreg):
        g.phi[j] = 1e3
    zz = g.XYZ[..., 2]
    g.phi[1] = np.where(np.abs(zz - L / 2) < 4 * dx, -1.0, 1.0)   # 贯穿 x-y 的薄层
    g.init_parent()
    ax = g.wrap_axes(1)
    ok1 = (0 in ax) and (1 in ax)
    print('  T12-A1 贯通 x-y 的薄层 ⇒ wrap_axes = %s（须含 0 与 1）: %s'
          % (ax, 'PASS' if ok1 else 'FAIL'))

    # --- A2 负对照：球（不贯通） ---
    g2, _ = mk(N, dx)
    g2.seed_sphere(1, [L / 2] * 3, 0.2 * L)
    g2.init_parent()
    ax2 = g2.wrap_axes(1)
    ok2 = (ax2 == [])
    print('  T12-A2 半径 0.2L 的球 ⇒ wrap_axes = %s（须为空）: %s'
          % (ax2, 'PASS' if ok2 else 'FAIL'))
    # 半径 0.3L 的球：直径 0.6L < L ⇒ 仍不贯通
    g2b, _ = mk(N, dx)
    g2b.seed_sphere(1, [L / 2] * 3, 0.3 * L)
    g2b.init_parent()
    ax2b = g2b.wrap_axes(1)
    print('      半径 0.3L 的球 ⇒ %s（应仍为空；直径 0.6L < L）' % ax2b)

    # --- A3 硬失败 ---
    g2.wrap_strict = True
    try:
        g2.check_wrap(1)
        raised = False
    except RuntimeError as e:
        raised = True
        msg = str(e)
    ok3 = (not raised)   # 球不该触发
    g.wrap_strict = True
    try:
        g.check_wrap(1)
        raised2 = False
    except RuntimeError as e:
        raised2 = True
    ok3 &= raised2
    print('  T12-A3 硬失败：球（不绕）不抛 %s；薄层（绕）抛错 %s ⇒ %s'
          % (not raised, raised2, 'PASS' if ok3 else 'FAIL'))

    # --- A4 真实场景：小盒 + 长板条 ---
    print()
    print('  T12-A4 真实场景：长板条放进不同大小的盒子')
    for Nn, lab in ((48, '小盒'), (128, '大盒')):
        dxn = 5.0e-8
        Ln = Nn * dxn
        gg = W.LevelSetMulti(Nn, Ln, C=None, eps0=None, gamma=0.15, Mob=1e-9,
                             df=[0.0, 1e8], workers=1, reinit_every=0, nv=1)
        plat = 4.0e-6                     # 板条长 4 µm
        R = 0.25e-6
        try:
            gg.seed_plate(1, [Ln / 2] * 3, [0.0, 1.0, 0.0], R, 2 * R,
                          elong=plat / 2 / R, along=[1.0, 0.0, 0.0], flat_end=True)
        except ValueError as e:
            print('     %s L=%.1f µm：seed_plate 直接拒绝（%s）'
                  % (lab, Ln * 1e6, str(e)[:60]))
            continue
        gg.init_parent()
        axx = gg.wrap_axes(1)
        ext, _ = gg.region_extent(1)
        print('     %s L=%.1f µm（板条长 %.1f µm，L/板条=%.2f）⇒ wrap_axes=%s，'
              '朴素包围盒=%s µm'
              % (lab, Ln * 1e6, plat * 1e6, Ln / plat, axx,
                 None if ext is None else np.round(ext * 1e6, 2)))
    print()
    print('=' * 100)
    print('  T12-A1 %s | T12-A2 %s | T12-A3 %s'
          % tuple('PASS' if x else 'FAIL' for x in (ok1, ok2, ok3)))
    allok = ok1 and ok2 and ok3
    print('  ⇒ T12-D12a %s' % ('PASS' if allok else 'FAIL'))
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
