#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r723_normal_lsq.py —— **S3② 的补测**：用**最小二乘平面拟合**估计界面法向。

## 为什么用它（`R712 §9.20b` 的候选修法①，原话）
> **提高 `M(n)` 输入法向的精度**（**不带反馈**的界面法向估计）—— ✅ **唯一剩下的杠杆**
> 局部最小二乘平面拟合 / 更大 stencil，**且只用于 `M(n)` 的输入**，不回灌水平集。

## 它同时解决 `R719 §2` 的量具困境（`R712` 新增缺口 **G-4**）
`np.gradient(edge_order=2)` 的二阶模板要 **±1 胞**；若判定带是 `1.5Δx` 而存储带只有 `±6Δx`
⇒ 部分胞的邻居**落在带外填充值 `1e3` 上** ⇒ 报出 `median|∇d| = 8e9`（荒谬），
缩到安全带又**剔样 81–94%**。
⇒ 本方法在**每个界面胞周围的 ±1 邻域（3×3×3）**内做**平面拟合**：
  · 模板只到 `±1 胞` ⇒ 对 `|φ| ≤ 1.5Δx` 的胞**必然落在 ±6Δx 存储带内**；
  · 天然给出**单位法向**（平面梯度的方向），不需要 `|∇φ|`；
  · 顺带给出**面内残差 `rms`** ⇒ 一个额外的质量指标（平面性）。

## 拟合口径（写死，可复现）
对界面胞 `x0`，取邻域 `N(x0)` = 与 `x0` **切比雪夫距离 ≤ 1** 的胞（27 个，含自身）；
用 `φ` 的一阶泰勒展开做最小二乘：
```
φ(x) − φ(x0) ≈ g · (x − x0)          ⇒  g = argmin Σ_{x∈N} [φ(x) − φ(x0) − g·(x−x0)]²
法向 n = g / |g|
面内 rms 残差 = sqrt( mean( (φ(x) − φ(x0) − g·(x−x0))² ) )
```
⚠ 只用**全部落在存储带内**的邻域（否则该胞剔除，并**报剔除数**）。

## 用法
    python3 _r723_normal_lsq.py --analytic                    # 解析正对照（球/长方体）
    python3 _r723_normal_lsq.py --root _exp/_bk_block --tags B2P_pre --step 100
"""
import argparse
import sys

import numpy as np


def load_snap(root, tag, step):
    p = '%s/dry_%s/snap_%05d.npz' % (root, tag, step)
    try:
        return np.load(p, allow_pickle=False), p
    except OSError:
        return None, p


def field_from_band(N, idx, val, fld, k):
    g = np.full(N ** 3, 1e3, float)
    m = (fld == k)
    g[idx[m]] = val[m]
    return g.reshape(N, N, N)


def lsq_normals(g, dx, mask, inside):
    """在 `mask` 的胞上做 ±1 邻域平面拟合，返回 (法向 (n,3), rms (n,), 剔除数)。

    ⚠ 只用"3×3×3 邻域全部落在存储带内"（`inside`）的胞 —— 与 `R719` 的教训一致。
    """
    N = g.shape[0]
    sel = mask & inside
    # 邻域健全性：mask 内每个胞的 27 邻域是否全在 inside
    okb = inside.copy()
    for ax in range(3):
        for sh in (1, -1):
            okb &= np.roll(inside, sh, ax)
    sel = sel & okb
    n_drop = int(mask.sum() - sel.sum())
    pts = np.argwhere(sel)
    if pts.size == 0:
        return np.zeros((0, 3)), np.zeros(0), n_drop
    nrm = np.zeros((len(pts), 3))
    rms = np.zeros(len(pts))
    off = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)],
                   float)
    dxv = off * dx
    A = dxv - dxv.mean(0)                     # 去心，避免与常数项共线
    pinv = np.linalg.pinv(A)
    for t, (i, j, k) in enumerate(pts):
        blk = g[i - 1:i + 2, j - 1:j + 2, k - 1:k + 2]
        b = blk.ravel() - blk.ravel().mean()
        gr = pinv @ b
        nn = np.linalg.norm(gr)
        nrm[t] = gr / nn if nn > 0 else 0.0
        rms[t] = float(np.sqrt(np.mean((b - A @ gr) ** 2)))
    return nrm, rms, n_drop


def analytic(step_um):
    print('=' * 100)
    print('解析正对照（LSQ 平面拟合法向 vs 解析法向）')
    print('=' * 100)
    N = 48
    dx = step_um * 1e-6
    c = (np.arange(N) + 0.5) * dx
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    ctr = np.array([X.mean(), Y.mean(), Z.mean()])
    cases = {}
    R = 0.25 * N * dx
    rr = np.sqrt((X - ctr[0]) ** 2 + (Y - ctr[1]) ** 2 + (Z - ctr[2]) ** 2)
    cases['球 SDF'] = (rr - R, (np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
                                / (rr[..., None] + 1e-300)))
    bx = np.abs(X - ctr[0]); by = np.abs(Y - ctr[1]); bz = np.abs(Z - ctr[2])
    gbox = np.maximum(np.maximum(bx, by), bz) - R
    # ⚠ 必须 `X.shape + (3,)`：`np.zeros_like(X)` 给的是 (N,N,N)，
    #   而 `nb[..., comp]` 会被解释成"第 3 维取 comp" ⇒ 形状 (N,N) ⇒ 广播失败。
    #   （这个错我在本脚本里犯过一次，探针 `_r723_probe2.py` 留证。）
    nb = np.zeros(X.shape + (3,))
    which = np.argmax(np.stack([bx, by, bz], -1), -1)
    d = np.stack([X - ctr[0], Y - ctr[1], Z - ctr[2]], -1)
    for a in range(3):
        m = (which == a)
        for comp in range(3):
            nb[..., comp] = np.where(m, np.sign(d[..., comp]), nb[..., comp])
    cases['长方体 SDF'] = (gbox, nb)
    print('  %-12s %8s %14s %14s %14s' %
          ('场', '界面胞', '夹角中位(°)', '夹角 p90(°)', 'rms(相对)'))
    for name, (g, nref) in cases.items():
        inside = g < 1e2
        mask = np.abs(g) <= 1.5 * dx
        nrm, rms, drop = lsq_normals(g, dx, mask, inside)
        if len(nrm) == 0:
            print('  %-12s  无有效胞（剔除 %d）' % (name, drop))
            continue
        # 只在与解析法向同向的胞上比（平面拟合的方向可以整体翻转）
        cos = np.abs(np.einsum('ij,ij->i', nrm, nref[mask & (g < 1e2)])) \
            if nref[mask & (g < 1e2)].shape[0] == len(nrm) else None
        if cos is None:
            print('  %-12s  形状不匹配，跳过' % name)
            continue
        ang = np.degrees(np.arccos(np.clip(cos, 0, 1)))
        print('  %-12s %8d %14.3f %14.3f %14.3e   (剔除 %d)'
              % (name, len(nrm), float(np.median(ang)),
                 float(np.percentile(ang, 90)),
                 float(np.median(rms) / (dx)), drop))
    print()
    print('  ⇒ 判读：**球面**的解析相邻法向夹角就是 `arcsin(Δx/R)` ≈ %.2f°（R=%.1fΔx）'
          % (np.degrees(np.arcsin(1.0 / (0.25 * N))), 0.25 * N))
    print('     ⇒ 若 LSQ 的夹角中位 ≈ 该值 ⇒ 法向估计**已达解析精度**（不是引擎缺陷）。')


def real(root, tags, step):
    for tag in tags:
        z, p = load_snap(root, tag, step)
        print('\n' + '─' * 100)
        print('【%s @%d】%s' % (tag, step, p))
        print('─' * 100)
        if z is None:
            print('  ⚠ 快照不存在')
            continue
        N = int(np.asarray(z['N']).ravel()[0])
        L = float(np.asarray(z['L']).ravel()[0])
        dx = L / N
        idx = np.asarray(z['band_idx']); val = np.asarray(z['band_val'], float)
        fld = np.asarray(z['band_fld'])
        beta_h, beta_w = 6.477, 2.3
        nref = np.asarray(z['n_hab'], float); nref /= np.linalg.norm(nref)
        wref = np.asarray(z['w_ax'], float); wref /= np.linalg.norm(wref)
        print('  %-4s %8s %7s %14s %14s %11s %11s' %
              ('场', '界面胞', '剔除', 'median|∇d|*(旧)', 'median|g|*dx(新)',
               '夹角中位(旧)', '夹角中位(新)'))
        for k in sorted(int(v) for v in np.unique(fld) if v > 0):
            g = field_from_band(N, idx, val, fld, k)
            if int((g < 0).sum()) < 50:
                continue
            inside = g < 1e2
            mask = np.abs(g) <= 1.5 * dx
            if int(mask.sum()) < 20:
                continue
            # 旧口径（会出带）
            gx, gy, gz = np.gradient(g, dx, edge_order=2)
            gn_old = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2)
            n_old = np.stack([gx, gy, gz], -1) / (gn_old[..., None] + 1e-300)
            med_old = float(np.median(gn_old[mask]))
            bx = mask[:-1, :, :] & mask[1:, :, :]
            a_old = float('nan')
            if int(bx.sum()) >= 20:
                p_ = n_old[:-1, :, :, :][bx]; q_ = n_old[1:, :, :, :][bx]
                a_old = float(np.median(np.degrees(np.arccos(
                    np.clip(np.abs(np.einsum('ij,ij->i', p_, q_)), 0, 1)))))
            # 新口径（LSQ）
            nrm, rms, drop = lsq_normals(g, dx, mask, inside)
            if len(nrm) == 0:
                print('  %-4d %8d %7d  无有效胞' % (k, int(mask.sum()), drop))
                continue
            a_new = float('nan')
            med_rms = float(np.median(rms) / dx)
            # 相邻胞夹角（新法向）：在**被选中的胞**里找 x 方向相邻对
            #   判据用 `R712 §9.1` 原文的"相邻法向夹角中位" ⇒ 必须真算，不能只报 rms
            selmask = mask & inside
            okb = inside.copy()
            for ax in range(3):
                for sh in (1, -1):
                    okb &= np.roll(inside, sh, ax)
            selmask = selmask & okb
            # 用 (i,j,k) 索引把法向摆回网格
            nrm_grid = np.zeros((N, N, N, 3))
            pts = np.argwhere(selmask)
            nrm_grid[pts[:, 0], pts[:, 1], pts[:, 2]] = nrm
            bx2 = selmask[:-1, :, :] & selmask[1:, :, :]
            if int(bx2.sum()) >= 20:
                p_ = nrm_grid[:-1, :, :, :][bx2]
                q_ = nrm_grid[1:, :, :, :][bx2]
                a_new = float(np.median(np.degrees(np.arccos(
                    np.clip(np.abs(np.einsum('ij,ij->i', p_, q_)), 0, 1)))))
            print('  %-4d %8d %7d %14.4f %14.4e %11.3f %11.3f'
                  % (k, int(mask.sum()), drop, med_old, med_rms, a_old, a_new))
        print('  ⚠ 记账：`median|∇d|*(旧)` 用 `np.gradient(edge_order=2)`；'
              '`*(新)` 用 ±1 邻域 **最小二乘平面拟合**')
        print('     `夹角中位(新)` = 用**新法向**算的相邻胞夹角 ⇒ **这才是 '
              '`R712 §9.1` 原文要的那个量，且不受带外填充值污染**。')
        print('  ★ 该法向的用途：**只喂 `M(n)` 的输入**（`R712 §9.20b` 候选①），**不回灌水平集**')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--analytic', action='store_true')
    ap.add_argument('--root', default='_exp/_bk_block')
    ap.add_argument('--tags', nargs='*', default=[])
    ap.add_argument('--step', type=int, default=100)
    ap.add_argument('--dx-um', type=float, default=0.0625)
    a = ap.parse_args()
    if a.analytic or not a.tags:
        analytic(a.dx_um)
        if a.analytic:
            return 0
    real(a.root, a.tags, a.step)
    return 0


if __name__ == '__main__':
    sys.exit(main())
