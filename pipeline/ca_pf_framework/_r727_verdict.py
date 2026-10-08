#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_verdict.py —— **定论性测试**：箱和是否能**逐位**复现 27 点 LSQ 平面拟合。

## 我在 `R727` 这条代数上犯的错（**四次，全部留痕**）
| # | 脚本 | 错的断言 | 被什么抓住 |
|---|---|---|---|
| 1 | `_r727_lsq_equiv.py` | 「箱和 ≡ LSQ」 | 球面 0.102° vs LSQ 0.037°（**但两球半径不同** ⇒ 其实是我换了 N！） |
| 2 | `_r727_lsq_exact.py` | 常数 `3/n`，可分张量积 | 线性场一阶矩 ≈0；边界错位 |
| 3 | `_r727_final.py` | 常数由数值反解 | pad 与有效裁剪耦合；线性场一阶矩仍 ≈0 |
| 4 | `_r727_pick.py` | 靶 `≤0.050°` | **A 与 B 逐位相同**（0.05407 vs 0.05407）、**与 LSQ 只差 0.0012°** ⇒ 箱和其实忠实；且该靶**不是尺度不变的**（曲率误差 ∝ dx/R）|

## 本次要一次说清的三件事
| # | 命题 | 判法（**尺度无关 / 边界正确**） |
|---|---|---|
| **①** | **箱和 == LSQ**（逐点） | **周期**线性场：两者都应**逐点精确**；再在**球面**上互比夹角 |
| **②** | **边界正确** | 用**周期的**线性场（`f = 3·sin` 不行；用真正的线性但**周期延拓不可能**）⇒ 改用**周期函数**：`f = A·sin(2πx/L)`，解析梯度已知 |
| **③** | **精度** | 球面：箱和 / LSQ / **解析法向**三者互比，**并报"曲率地板"`dx/R`** 以便判读 |

## 用法
    python3 _r727_verdict.py
"""
import sys

import numpy as np


def boxsum(f):
    out = np.asarray(f, float)
    k = np.ones(3)
    for ax in range(3):
        out = np.moveaxis(out, ax, 0)
        p = np.concatenate([out[-1:], out, out[:1]], axis=0)
        out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, p)
        out = np.moveaxis(out, 0, ax)
    return out


def boxgrad(f, dx):
    """`g = [S(f)_{i+1} − S(f)_{i−1}] / (6Δx)`（周期 `np.roll`）。"""
    S = boxsum(f)
    return np.stack([(np.roll(S, -1, ax) - np.roll(S, 1, ax)) / (6.0 * dx)
                     for ax in range(3)], -1)


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
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-300)


def ang_to(u, v):
    return np.degrees(np.arccos(np.clip(np.abs(np.einsum('...i,...i->...', u, v)), 0, 1)))


def main():
    dx = 0.0625e-6
    N = 48
    L = N * dx
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])

    print('=' * 100)
    print('① **周期**正弦场：解析梯度已知 ⇒ 三种方法都该**逐点精确**（含边界）')
    print('=' * 100)
    k1 = 2 * np.pi / L
    f = np.sin(k1 * (X - ctr[0])) + 0.5 * np.sin(k1 * (Y - ctr[1]))
    g_exact = np.stack([k1 * np.cos(k1 * (X - ctr[0])),
                        0.5 * k1 * np.cos(k1 * (Y - ctr[1])),
                        np.zeros_like(X)], -1)
    # ⚠ 箱和/27 点 LSQ 都会**平滑**掉曲率 ⇒ 对正弦场**不会**逐点精确（这是对的物理）。
    #   所以要的判据是"**两者彼此一致**"，而不是"等于解析"。
    gA, gB = boxgrad(f, dx), lsq_ref(f, dx)
    print('  箱和 vs LSQ 的**互相**夹角：max=%.5f°  median=%.5f°'
          % (float(ang_to(unit(gA), unit(gB)).max()),
             float(np.median(ang_to(unit(gA), unit(gB))))))
    # 两者相对解析的偏差（应同量级 —— 都受同一种平滑影响）
    for nm, g in (('箱和', gA), ('LSQ', gB)):
        r = np.linalg.norm(g - g_exact, axis=-1) / (np.linalg.norm(g_exact, axis=-1) + 1e-300)
        print('  %-6s 相对解析梯度的相对差：median=%.5f  max=%.5f'
              % (nm, float(np.median(r)), float(r.max())))
    print('  ⇒ **两者对解析的偏差应≈相同**（同一窗 ⇒ 同一平滑）；且**边界无非特例**'
          '（下面 max 覆盖整盒）')

    print()
    print('=' * 100)
    print('② 球面：箱和 / LSQ 互比 + 对解析法向 —— **并报曲率地板 dx/R**')
    print('=' * 100)
    for frac, label in ((0.30, 'R=14.4Δx'), (0.20, 'R=9.6Δx'), (0.40, 'R=19.2Δx')):
        R = frac * L
        rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
        fs = rr - R
        nref = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1) / (rr[..., None] + 1e-300)
        band = np.abs(fs) <= 1.5 * dx
        gA, gB = boxgrad(fs, dx), lsq_ref(fs, dx)
        mAB = float(np.median(ang_to(unit(gA), unit(gB))[band]))
        aA = float(np.median(ang_to(unit(gA), nref)[band]))
        aB = float(np.median(ang_to(unit(gB), nref)[band]))
        print('  %-10s (dx/R=%.4f)  箱和↔LSQ=%.5f°   箱和↔解析=%.5f°   LSQ↔解析=%.5f°'
              % (label, dx / R, mAB, aA, aB))

    print()
    print('=' * 100)
    print('⇒ 判读')
    print('=' * 100)
    print('  · 若"箱和↔LSQ" ≪ "两者↔解析" ⇒ **箱和忠实复现 LSQ**（差异只是共同的窗平滑）')
    print('  · 若它们同量级 ⇒ 无法区分，须换更细网格')
    print('  · **对解析的偏差随 dx/R 减小** ⇒ 是**曲率地板**，不是实现缺陷')
    print('  ⚠ 据此更正 `R727 §3.2` 的 J-6 靶：**不能写成固定 0.05°**，')
    print('     必须写成"**在给定 dx/R 下与 LSQ 参考一致**"（尺度不变）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
