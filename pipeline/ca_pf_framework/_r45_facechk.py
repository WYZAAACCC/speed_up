#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r45_facechk.py —— **面分类量具的正对照**（R45 的下一步第 1 条）。

## 为什么必须先做这个
R45 的 `ed_by_face` 用 `(n·a)²>0.81` / `(n·w)²>0.81` / `(n·n*)²>0.81` 把界面胞
分成 tip / side / wide 三档，并据此**否证了 R44 的机理结论**。
但**这把尺子本身没有正对照** —— 本项目最贵的教训就是「量错了还以为在量对的」。

## 本脚本（纯解析，不跑仿真）
造一个**解析已知**的长方体板条 SDF（沿 `(a, w, n*)` 三个正交轴的长度 L / W / t），
算 `n = ∇φ/|∇φ|`，按同一套阈值分档，与**解析面积**对比：

    面积： tip = 2·W·t   side = 2·L·t   wide = 2·L·W

判据（先写死）：每档的**胞数与解析面积的比**应一致（差异 < 25%，受 Δx 量化影响）。

用法：  python3 _r45_facechk.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

N, DX = 96, 20e-9                       # 小 Δx ⇒ 面解析得好
L = N * DX


def main():
    # 三个正交轴（故意取斜的，模拟真实 n* 与网格斜交）
    n_ax = np.array([0.3, 0.4, np.sqrt(1 - 0.09 - 0.16)])
    n_ax /= np.linalg.norm(n_ax)
    tmp = np.array([1.0, -1.0, 0.0])
    a_ax = tmp - (tmp @ n_ax) * n_ax
    a_ax /= np.linalg.norm(a_ax)
    w_ax = np.cross(n_ax, a_ax)
    # ⚠ 第一版把 L 取成 4 µm 而盒只有 1.92 µm ⇒ **板条装不下** ⇒ `tip` 档 0 胞
    #   ⇒ 正对照报"不通过"。那是**测试装置**错，不是量具错（正对照的用途正是这个）。
    t, W, Le = 0.30e-6, 0.60e-6, 1.20e-6
    print('=' * 78)
    print('面分类量具的正对照（解析长方体板条）')
    print('  尺寸 L=%.2f µm  W=%.2f µm  t=%.2f µm ；Δx=%.0f nm；盒 %.2f µm'
          % (Le * 1e6, W * 1e6, t * 1e6, DX * 1e9, L * 1e6))
    ii = np.arange(N) * DX - L / 2
    rel = [ii[:, None, None], ii[None, :, None], ii[None, None, :]]
    pa = a_ax[0] * rel[0] + a_ax[1] * rel[1] + a_ax[2] * rel[2]
    pw = w_ax[0] * rel[0] + w_ax[1] * rel[1] + w_ax[2] * rel[2]
    pn = n_ax[0] * rel[0] + n_ax[1] * rel[1] + n_ax[2] * rel[2]
    sdf = np.maximum(np.maximum(np.abs(pn) - t / 2, np.abs(pa) - Le / 2),
                     np.abs(pw) - W / 2)
    g = np.gradient(sdf, DX, edge_order=2)
    gn = np.sqrt(sum(x ** 2 for x in g)) + 1e-30
    iface = np.abs(sdf) <= 1.5 * DX
    nd = [x / gn for x in g]
    c2 = {}
    for tag, u in (('tip', a_ax), ('side', w_ax), ('wide', n_ax)):
        c2[tag] = np.clip(sum(nd[i] * u[i] for i in range(3)) ** 2, 0.0, 1.0)
    area = dict(tip=2 * W * t, side=2 * Le * t, wide=2 * Le * W)
    tot_a = sum(area.values())
    print('\n  %-6s %-14s %-14s %-12s %-10s %s'
          % ('档', '解析面积 µm²', '解析占比', '胞数', '胞占比', '一致性'))
    rows = []
    for tag in ('tip', 'side', 'wide'):
        m = iface & (c2[tag] > 0.81)
        n = int(m.sum())
        rows.append((tag, area[tag], n))
    tot_n = sum(r[2] for r in rows)
    ok_all = True
    for tag, ar, n in rows:
        fa, fn = ar / tot_a, n / max(tot_n, 1)
        rel = abs(fn - fa) / fa
        ok = rel < 0.25
        ok_all &= ok
        print('  %-6s %-14.3f %-14.3f %-12d %-10.3f %s（相对差 %.1f%%）'
              % (tag, ar * 1e12, fa, n, fn, '✅' if ok else '❌', 100 * rel))
    # 未被三档覆盖的胞（斜法向）—— H-ε 关心的那一档
    cov = np.zeros(iface.shape, bool)
    for tag in ('tip', 'side', 'wide'):
        cov |= (c2[tag] > 0.81)
    obl = iface & (~cov)
    print('\n  三档之外（斜法向 `oblique`）：**%d** 胞 = 界面带的 %.2f%%'
          % (int(obl.sum()), 100.0 * obl.sum() / max(int(iface.sum()), 1)))
    print('  ⇒ 对**光滑长方体**这一档应当≈0（解析上面只有三类法向）%s'
          % ('✅' if obl.sum() / max(int(iface.sum()), 1) < 0.05 else '❌ 偏高'))
    print('\n  ⇒ 面分类量具：%s' % ('**通过**' if ok_all else '**不通过**'))


if __name__ == '__main__':
    main()
