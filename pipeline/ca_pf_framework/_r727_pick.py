#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_pick.py —— **用数值在两个候选形式里选**（不再手推代数）。

## 背景：我在这条代数上连续错了三次（`_r727_lsq_equiv` / `_r727_lsq_exact` / `_r727_final`）
每次都栽在"归一化常数 / 边界 pad / 核翻转"上。**手工推导已被证明不可靠。**
⇒ 改为：**把两个候选形式都实现出来，用 `_r723` 已验证过的 `LSQ 平面拟合`（球面 0.037°）
   当裁判**，谁接近它就用谁；都不接近就**如实报 FAIL**。

## 两个候选
| 候选 | 形式 | 说明 |
|---|---|---|
| **A** | `g = (1/6Δx)·[S(d)_{i+1} − S(d)_{i−1}]`，`S` = 3³ **周期**箱和 | 最简（`R727 §2.1` 的原式） |
| **B** | `np.gradient(d)` 后再对**分量**做 3³ 箱和（= 引擎既有 `norm_smooth=1`） | 上游 `R12-a` 判它会造碎片，但**精度**未知 |

## 裁判
`LSQ 平面拟合`（27 点，`pinv`）—— `_r723_normal_lsq.py` 已验：球面 **0.037°**、长方体 **0.000°**、剔除 0。

## 判据（**先登记**）
| # | 命题 |
|---|---|
| **J-6a** | 候选 A 在球面上 **≤ 0.05°** |
| **J-6b** | 候选 B 在球面上 **≤ 0.05°** |
| **J-6c** | 至少一个候选 **≤ 0.05°**（否则本方案在该形式上 FAIL） |

## 用法
    python3 _r727_pick.py
"""
import sys

import numpy as np


def boxsum(f):
    """3³ **周期**箱和（可分离，用 `np.correlate` —— 对称核，翻转无影响）。"""
    out = np.asarray(f, float)
    k = np.ones(3)
    for ax in range(3):
        out = np.moveaxis(out, ax, 0)
        p = np.concatenate([out[-1:], out, out[:1]], axis=0)
        out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
        out = np.moveaxis(out, 0, ax)
    return out


def cand_A(f, dx):
    S = boxsum(f)
    out = []
    for ax in range(3):
        out.append((np.roll(S, -1, ax) - np.roll(S, 1, ax)) / (6.0 * dx))
    return np.stack(out, -1)


def cand_B(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.stack([boxsum(g[i]) / 27.0 for i in range(3)], -1)


def lsq_ref(f, dx):
    off = np.array([(i, j, k) for i in (-1, 0, 1)
                    for j in (-1, 0, 1) for k in (-1, 0, 1)], float) * dx
    A = off - off.mean(0)
    pinv = np.linalg.pinv(A)
    N = f.shape[0]
    fp = np.pad(f, 1, mode='wrap')
    blk = np.stack([fp[i:i + N, j:j + N, k:k + N]
                    for i in range(3) for j in range(3) for k in range(3)], -1)
    b = blk - blk.mean(-1, keepdims=True)
    return np.einsum('ij,...j->...i', pinv, b)


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-300
    return v / n


def main():
    dx = 0.0625e-6
    N = 32
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])

    # ── 前置：线性场正对照（三种方法都该给出精确梯度） ──
    print('=' * 100)
    print('前置正对照：线性场 f = 3(x−x̄)+5(y−ȳ)−2(z−z̄)，三种方法都应精确')
    print('=' * 100)
    lin = 3.0 * (X - ctr[0]) + 5.0 * (Y - ctr[1]) - 2.0 * (Z - ctr[2])
    for nm, g in (('A 箱和', cand_A(lin, dx)), ('B 先梯度后箱和', cand_B(lin, dx)),
                  ('LSQ 参考', lsq_ref(lin, dx))):
        err = np.abs(g - np.array([3.0, 5.0, -2.0])).max()
        print('  %-18s 整盒 max|g−解析| = %.4e  ⇒ %s'
              % (nm, err, '✅' if err < 1e-9 else '⚠ 边界/常数有差'))

    # ── 球面 ──
    print()
    print('=' * 100)
    print('球面：候选 A / B / LSQ 参考 对**解析法向**的夹角（界面带 |f| ≤ 1.5Δx）')
    print('=' * 100)
    R = 0.30 * N * dx
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    f = rr - R
    nref = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1) / (rr[..., None] + 1e-300)
    band = np.abs(f) <= 1.5 * dx
    res = {}
    for nm, g in (('A 箱和', cand_A(f, dx)), ('B 先梯度后箱和', cand_B(f, dx)),
                  ('LSQ 参考', lsq_ref(f, dx))):
        ca = np.clip(np.abs(np.einsum('...i,...i->...', unit(g), nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))[band]
        res[nm] = float(np.median(ang))
        print('  %-18s median=%.5f°  p90=%.5f°' % (nm, res[nm],
              float(np.percentile(ang, 90))))

    # ── 判定 ──
    print()
    print('=' * 100)
    print('判定（靶 ≤ 0.050°）')
    print('=' * 100)
    a_ok = res['A 箱和'] <= 0.05
    b_ok = res['B 先梯度后箱和'] <= 0.05
    print('  J-6a 候选 A：%.5f°  ⇒ %s' % (res['A 箱和'], '✅ PASS' if a_ok else '⛔ FAIL'))
    print('  J-6b 候选 B：%.5f°  ⇒ %s' % (res['B 先梯度后箱和'], '✅ PASS' if b_ok else '⛔ FAIL'))
    print('  J-6c 至少一个通过：%s' % ('✅ PASS' if (a_ok or b_ok) else '⛔ **FAIL**'))
    if not (a_ok or b_ok):
        print()
        print('  ⇒ ⛔ **两个候选都不达标** ⇒ 本方案在这两种"箱和"形式上都 FAIL。')
        print('     ⇒ 可行路线只剩：**逐点 27 点 LSQ（`pinv`）**，但它比箱和贵得多')
        print('       ⇒ 须先做**代价估计**再决定是否接进引擎（`R727 §5-6` 已登记该风险）')
    return 0 if (a_ok or b_ok) else 1


if __name__ == '__main__':
    sys.exit(main())
