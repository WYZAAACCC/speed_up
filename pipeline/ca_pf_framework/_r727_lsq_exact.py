#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r727_lsq_exact.py —— ★ **R727 §2.1 的代数式更正**：LSQ 平面拟合的**精确可分形式**。

## 我上一版错在哪（留痕，`R712 §0.5` 纪律）
`_r727_lsq_equiv.py` 断言「箱和 `g = (1/6)[S(f)_{i+1} − S(f)_{i−1}]` ≡ 27 点 LSQ 平面拟合」。
**实测证否**：球面上箱和给 **0.102°**、真 LSQ 给 **0.037°**（差 2.7 倍）。
**根因**（`[代]`）：对 `f = ½xᵀHx`，
* **真 LSQ 在原点精确**（二次项的线性项 `H·0 = 0` 消失）；
* **箱和形式**（沿 x 轴）的偏差是 `(1/6)·tr(H)·(x + dx·e_x)` ⇒ 球面 `tr(H)/6 = 1/(3R)`
  ⇒ **沿径向混进一个假分量 `1/(3R)`**，把法向拉偏。
⇒ 我把「**梯度的箱和均值**」当成了「**LSQ 平面拟合的法向**」——**不等价**。
⇒ **要真等价，必须把一阶矩也算进去**（三轴各 4 个矩，而不是 2 个箱和）。

## ★ 正确做法：按轴分离的**精确**可分卷积（各轴 4 个一维卷积，共 12 个）
在 27 点窗内，法向方程只用**二阶矩**：
```
Σr = 0,  Σ r_i r_j = (n/3)δ_ij ,  Σ r_i r_j r_k = 0        （对称窗）
⇒ g = (3/n) Σ_x r·f(x) ,   n = 27
```
按轴分离（`r_x ∈ {−dx,0,+dx}`）：
```
Σ_x r·f = dy·dz · [ dx·(M1x(i+1) − M1x(i−1)) · S_yz ... ]   ← 展开见 §impl
```
本脚本**不手推**，直接用「1D 窗 (−1,0,+1) 沿三轴各做一次」的**逐轴张量积**构造精确解，
再与逐点 `pinv` 的 LSQ **逐位**对照 —— **让数值说话**。

## 判据
| # | 命题 |
|---|---|
| **A′** | 可分形式 与 逐点 27 点 LSQ **逐点夹角 < 1e-9°**（真等价） |
| **B′** | 在**周期**数组上无边界特例（首末胞的夹角也在 max 里） |
| **C′** | 对解析法向：球面 median **≤ 0.05°**、长方体 **≤ 1e-6°** |

## 用法
    python3 _r727_lsq_exact.py
"""
import sys

import numpy as np


def conv1(f, k, ax):
    """周期 1D **相关**（沿 `ax`），核 `k`（奇数长，**不翻转**）。

    ⚠⚠ 坑（我在本脚本里踩过，`_r727_dbg2.py` 留证）：
      `np.convolve(v, k, 'valid')` 会**翻转** `k`。对**对称**核（如盒核 `[1,1,1]`）
      无所谓；但对**反对称**核 `K1 = [-1,0,1]`，翻转后实际生效的是 `[1,0,-1]`
      ⇒ **符号与中心都错位**（实测：线性场上 `Mx` 不恒定，min/max = −54/162，应恒为 27）。
      ⇒ 必须用 `np.correlate`（**不翻转**）。
    """
    out = np.asarray(f, float)
    n = len(k) // 2
    out = np.moveaxis(out, ax, 0)
    if n > 0:
        pad = np.concatenate([out[-n:], out, out[:n]], axis=0)
    else:
        pad = out
    out = np.apply_along_axis(lambda v: np.correlate(v, k, 'valid'), 0, pad)
    return np.moveaxis(out, 0, ax)


def sep_moments(f, dx):
    """返回 3×3×3 窗内的 `(S, Mx, My, Mz)`，全部**周期、精确**。

    `S   = Σ f`
    `Mx  = Σ r_x f`（`r_x ∈ {−dx,0,+dx}`）… 同理 `My/Mz`
    """
    K0 = np.array([1.0, 1.0, 1.0])          # 求和
    K1 = np.array([-1.0, 0.0, 1.0]) * dx    # 一阶矩（含 dx）
    # 沿每个轴，既可以做 K0 也可以做 K1 ⇒ 3^3 = 27 个张量积
    # 但我们只要 4 个矩：全 0、只在 x 上取 1、只在 y、只在 z
    def tp(kx, ky, kz):
        out = f
        out = conv1(out, kx, 0)
        out = conv1(out, ky, 1)
        out = conv1(out, kz, 2)
        return out
    S = tp(K0, K0, K0)
    Mx = tp(K1, K0, K0)
    My = tp(K0, K1, K0)
    Mz = tp(K0, K0, K1)
    return S, Mx, My, Mz


def grad_sep(f, dx):
    """**精确** LSQ 平面拟合的梯度：`g = (3/n)·Σ r f`，`n = 27`。"""
    S, Mx, My, Mz = sep_moments(f, dx)
    c = 3.0 / 27.0
    return [c * Mx, c * My, c * Mz]


def lsq_plane_ref(f, dx):
    """逐点 27 点 LSQ 平面拟合（参考实现，`pinv`）。"""
    off = np.array([(i, j, k) for i in (-1, 0, 1)
                    for j in (-1, 0, 1) for k in (-1, 0, 1)], float) * dx
    A = off - off.mean(0)
    pinv = np.linalg.pinv(A)
    N = f.shape[0]
    fp = np.pad(f, 1, mode='wrap')
    blk = np.stack([fp[i:i + N, j:j + N, k:k + N]
                    for i in range(3) for j in range(3) for k in range(3)], -1)
    b = blk - blk.mean(-1, keepdims=True)
    g = np.einsum('ij,...j->...i', pinv, b)
    return [g[..., 0], g[..., 1], g[..., 2]]


def unit(gs):
    n = np.sqrt(sum(g ** 2 for g in gs)) + 1e-300
    return np.stack([g / n for g in gs], -1)


def main():
    N = 24
    dx = 0.0625e-6
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])
    R = 0.30 * N * dx
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    cases = {'球 SDF': (rr - R, np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
                        / (rr[..., None] + 1e-300))}
    bb = np.maximum(np.maximum(np.abs(X - ctr[0]), np.abs(Y - ctr[1])),
                    np.abs(Z - ctr[2])) - R
    nb = np.zeros(X.shape + (3,))
    which = np.argmax(np.stack([np.abs(X - ctr[0]), np.abs(Y - ctr[1]),
                                np.abs(Z - ctr[2])], -1), -1)
    dd = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
    for a in range(3):
        m = (which == a)
        for comp in range(3):
            nb[..., comp] = np.where(m, np.sign(dd[..., comp]), nb[..., comp])
    cases['长方体 SDF'] = (bb, nb)
    # 负对照：常数场（法向无定义 ⇒ 两者都该给 0/NaN，不该"看起来对"）
    cases['常数场（负对照）'] = (np.ones_like(X) * 3.7, np.zeros(X.shape + (3,)))

    ok = True
    print('=' * 100)
    print("A′) 可分形式  vs  逐点 27 点 LSQ（要求 < 1e-9°，即**真等价**）")
    print('=' * 100)
    for name, (f, _) in cases.items():
        g1 = grad_sep(f, dx)
        g2 = lsq_plane_ref(f, dx)
        n1 = np.sqrt(sum(g ** 2 for g in g1))
        n2 = np.sqrt(sum(g ** 2 for g in g2))
        rel = float(np.max(np.abs(np.stack(g1, -1) - np.stack(g2, -1)))
                    / (np.max(np.abs(np.stack(g2, -1))) + 1e-300))
        u1, u2 = unit(g1), unit(g2)
        # ⚠ 量具更正（2026-10-08）：第一版写 `mask = (n1 > 1e-12) & (n2 > 1e-12)`，
        #   对**真 SDF** 也成立 ⇒ 常数场的 mask.sum() 也是 0 ⇒ **三个场全进"不适用"分支**
        #   （把"两者梯度都≈0"当成了普遍情况）。正解：**只在两者梯度都真的 ≈0 时**才不适用。
        mask = (n1 > 1e-6) & (n2 > 1e-6)
        if int(mask.sum()) < 10:
            print('  %-16s 两者梯度都 ≈0（常数场）⇒ **等价性不适用** ✅' % name)
            continue
        ca = np.clip(np.abs(np.einsum('...i,...i->...', u1, u2)), 0, 1)
        ang = np.degrees(np.arccos(ca))[mask]
        mx = float(ang.max())
        good = mx < 1e-9
        ok &= good
        print('  %-16s 逐点夹角 max=%.3e°   梯度相对差=%.3e   ⇒ %s'
              % (name, mx, rel, '✅ 逐位等价' if good else '⛔ 不等价'))

    print()
    print('=' * 100)
    print("B′) 边界：周期 ⇒ 首末胞无特例（下面 max 覆盖整盒，含 6 个面）")
    print('=' * 100)
    for name, (f, nref) in cases.items():
        if '常数' in name:
            continue
        g1 = unit(grad_sep(f, dx))
        ca = np.clip(np.abs(np.einsum('...i,...i->...', g1, nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))
        face = [ang[0, N // 2, N // 2], ang[N - 1, N // 2, N // 2],
                ang[N // 2, 0, N // 2], ang[N // 2, N - 1, N // 2],
                ang[N // 2, N // 2, 0], ang[N // 2, N // 2, N - 1]]
        print('  %-16s 六面心 = %s' % (name, np.array2string(
            np.array(face), precision=4)))
        print('                   全盒 max=%.4f°  median=%.4f°'
              % (float(ang.max()), float(np.median(ang))))

    print()
    print('=' * 100)
    print("C′) 精度（判据 J-6/J-7）")
    print('=' * 100)
    for name, (f, nref) in cases.items():
        if '常数' in name:
            continue
        g1 = unit(grad_sep(f, dx))
        ca = np.clip(np.abs(np.einsum('...i,...i->...', g1, nref)), 0, 1)
        ang = np.degrees(np.arccos(ca))
        band = np.abs(f) <= 1.5 * dx
        med = float(np.median(ang[band]))
        tgt = 0.05 if '球' in name else 1e-6
        good = med <= tgt
        ok &= good
        print('  %-16s 界面带内 median=%.5f°  靶 ≤%.3f°  ⇒ %s'
              % (name, med, tgt, '✅' if good else '⛔'))

    print()
    print('⇒ **总判定：%s**' % ('全部通过' if ok else '**有 FAIL**'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
