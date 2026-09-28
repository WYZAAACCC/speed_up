#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T12_verify_wrap2.py --- 绕盒守卫的**语义修正**验证（逐变体 vs 并集）。

修正内容
--------
`wrap_axes(None)`（并集）会把"**碰撞后变体网络渗流贯通**"误报成"板条绕盒"。
新增 `wrap_axes_any()`（逐变体）。本脚本用**两个能区分两种语义的对照**验证：

  **负对照（关键）**：构造"**并集贯通、但没有任何单个变体贯通**"的构型
      （每个胞独立随机赋变体号 ⇒ 每个变体是孤立散点；并集 = 全盒 ⇒ 渗流）
      ⇒ 并集口径**必须误报**（证明它有这个缺陷），逐变体口径**必须不报**（证明它修对了）
  **正对照**：构造"**单个变体跨越全盒**"的构型（一条贯穿的薄层）
      ⇒ 两个口径**都必须报**（证明逐变体口径不会漏报）

用法：python3 T12_verify_wrap2.py
退出码：0 = PASS
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import windowB_surface as W                                     # noqa: E402

N, dx = 48, 2.5e-8
L = N * dx


def mk():
    return W.LevelSetMulti(N, L, C=None, eps0=None, nv=12, gamma=0.15, Mob=1e-9,
                           df=[0.0] + [1e8] * 12, workers=1, reinit_every=0)


def set_reg(g, reg):
    """直接按区域号构造 φ（每个区域自己的指示场取负、其余取正）。"""
    for j in range(g.nreg):
        g.phi[j] = np.where(reg == j, -1.0, 1.0)


def main():
    print('=' * 100)
    print('绕盒守卫语义修正验证   N=%d  nv=12' % N)
    print('=' * 100)

    # ---- 负对照：并集贯通、单变体不贯通 ----
    g = mk()
    rng = np.random.default_rng(3)
    reg = 1 + rng.integers(0, 12, size=(N, N, N))       # 每胞独立随机 ⇒ 变体全是孤立点
    set_reg(g, reg)
    uni = g.wrap_axes(None)
    per = g.wrap_axes_any()
    print('【负对照】并集贯通 / 单变体不贯通（每胞独立随机）')
    print('    并集口径 wrap_axes(None)  = %s   ← 应**误报**（证明它有缺陷）' % uni)
    print('    逐变体 wrap_axes_any()    = %s   ← 应**为空**（证明修正有效）' % per)
    ok_neg = (len(uni) > 0) and (len(per) == 0)
    print('    ⇒ 负对照: %s' % ('PASS（并集误报、逐变体不报）' if ok_neg else 'FAIL'))

    # ---- 正对照：单个变体跨越全盒 ----
    g2 = mk()
    zz = g2.XYZ[..., 2]
    reg2 = np.zeros((N, N, N), np.int64)
    reg2[np.abs(zz - L / 2) < 4 * dx] = 1                # 变体 1 = 贯穿 x-y 的薄层
    reg2[(np.abs(zz - L / 2) >= 4 * dx)] = 2             # 其余全填变体 2（一块大体块）
    set_reg(g2, reg2)
    uni2 = g2.wrap_axes(None)
    per2 = g2.wrap_axes_any()
    print()
    print('【正对照】单个变体（1）贯穿全盒')
    print('    并集口径 = %s ; 逐变体 = %s   ← 两者都应报出轴 0、1' % (uni2, per2))
    ok_pos = (0 in uni2) and (0 in per2.get(1, [])) and (1 in per2.get(1, []))
    print('    ⇒ 正对照: %s' % ('PASS（都不漏报）' if ok_pos else 'FAIL'))

    # ---- 负对照 2：真实碰撞后的网络（用 T16 的构型不是必须；这里用棋盘渗流） ----
    g3 = mk()
    ii, jj, kk = np.indices((N, N, N))
    reg3 = 1 + ((ii // 2) + (jj // 2) + (kk // 2)) % 12   # 2³ 小块棋盘 ⇒ 并集全盒、单变体不连通
    set_reg(g3, reg3)
    uni3 = g3.wrap_axes(None)
    per3 = g3.wrap_axes_any()
    print()
    print('【负对照 2】2³ 小块棋盘（并集全盒、单变体不连通）')
    print('    并集口径 = %s ; 逐变体 = %s' % (uni3, per3))
    ok_neg2 = (len(per3) == 0)
    print('    ⇒ 逐变体不报: %s' % ('PASS' if ok_neg2 else 'FAIL'))

    print()
    print('=' * 100)
    allok = ok_neg and ok_pos and ok_neg2
    print('  ⇒ 语义修正 %s' % ('PASS' if allok else 'FAIL'))
    print('  ★ 记账：这条修正说明**守卫本身也要做正/负对照** ——')
    print('     `wrap_axes(None)` 的正对照（T12-A1，单区域薄层）是对的，')
    print('     但它**掩盖**了并集口径在多核渗流下的误报 ⇒ 已补进 MEASUREMENT_SPEC 的 R0。')
    print('=' * 100)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main())
