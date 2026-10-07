#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r195_c2p_phi.py —— ★ 用**真实 φ**（从 `band_*` 稀疏带重建）重量 `c2p = (n̂·ncmp)²`。

## 为什么必须用真 φ 而不是 `region` 重建

`§132.5` 用 `region` + 平滑指示场估法向，得到"各向同性"的结论，
但**估计量自身有偏**（零假设基准 0.241 而非理论 0.5）
⇒ 结论的**分辨力**可疑。**用真 φ 的梯度**就没有这个偏差。

## 数据来源（**更正 `§132.2`**）

`§132.2` 曾判"归档快照没有 φ"（P1-46）—— **错了**。
`_r194_bandscan.py` 实测：**全部归档臂**的末快照都含
`band_idx` / `band_val` / `band_fld` / `band_cells`（P0-4 的**带内稀疏 φ**）。
（第一版只看了 `list(keys())[:8]` ⇒ 把 `band_*` 截掉了 —— **第 10 个自查错误**。）

## 判据（**先写死**）

* **C-1（自洽正对照）**：用重建的 φ 算 `argmin_k φ_k`，在**带内**必须与归档的
  `region` **逐位相同**。⇒ 证明重建没有搞错场的编号/线性索引。
* **C-2（正对照）**：合成一个**平界面**（法向 = `ncmp`）的稀疏带 ⇒ `c2p` = 1。
* **C-3（零假设）**：合成**随机取向**的平界面 ⇒ 记录该口径下的基准（不是照抄 0.5）。
* **C-4（实测）**：真实快照的 `c2p` 分布，与 C-3 的基准比。
* **C-5（退化）**：带内胞不足 / 无变体-变体界面 ⇒ 说"不适用"，不是 ❌。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MB = os.path.join(HERE, '_exp', '_bk_mb')


def load_ncmp():
    from T16_verify_rve import C, EPS0
    import windowB_surface as W
    g = W.LevelSetMulti(8, 8e-9, C=np.asarray(C, float),
                        eps0=[np.asarray(e, float) for e in EPS0])
    return np.asarray(g.ncmp, float)


def rebuild(z):
    """从 `band_*` 重建**稀疏** φ：(nreg, N, N, N) 的 float 数组，带外 = NaN。"""
    N = int(z['N']) if 'N' in z else None
    if N is None:
        return None
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    fld = z['band_fld'].astype(int)
    idx = z['band_idx'].astype(int)
    val = z['band_val'].astype(np.float32)
    flat[fld, idx] = val
    return phi


def c2p_from_phi(phi, ncmp, dx, region=None):
    """用真 φ 的**中心差分**梯度算变体-变体界面的 `c2p`。返回 (c2p, 说明)。"""
    nf, N = phi.shape[0], phi.shape[1]
    # 对每一对相邻（在 6 邻域里接触的）场，用差分场 d = φ_i − φ_j 的梯度
    good = np.isfinite(phi).all(0)          # 三向邻居都有限才可靠
    out, info = [], []
    # 接触对：用**有限值**判定（带内两场都有限且相邻）
    fin = np.isfinite(phi)
    pairs = set()
    for i in range(1, nf):
        for j in range(i + 1, nf):
            both = fin[i] & fin[j]
            if both.sum() < 50:
                continue
            pairs.add((i, j))
    for (i, j) in sorted(pairs):
        nj = ncmp[j, i] if (j < ncmp.shape[0] and i < ncmp.shape[1]) else None
        if nj is None or not np.isfinite(nj).all() or not nj.any():
            continue
        nj = nj / np.linalg.norm(nj)
        d = phi[i] - phi[j]
        # 只在 d 的零等值面附近取（且三方向邻居都有限）
        gx = np.full_like(d, np.nan)
        for ax in range(3):
            sl_lo = [slice(None)] * 3
            sl_hi = [slice(None)] * 3
            sl_c = [slice(None)] * 3
            sl_lo[ax] = slice(0, N - 2)
            sl_hi[ax] = slice(2, N)
            sl_c[ax] = slice(1, N - 1)
            gx[tuple(sl_c)] = (d[tuple(sl_hi)] - d[tuple(sl_lo)]) / (2 * dx)
        # 用**差分场**的梯度作法向（恰好是界面法向，且跨界面两侧对称）
        g = np.stack([gx if ax == 0 else None for ax in range(3)], 0) \
            if False else None
        # 上面那行是占位；真正取三个分量
        comps = []
        for ax in range(3):
            c = np.full_like(d, np.nan)
            lo = [slice(None)] * 3
            hi = [slice(None)] * 3
            cc = [slice(None)] * 3
            lo[ax] = slice(0, N - 2)
            hi[ax] = slice(2, N)
            cc[ax] = slice(1, N - 1)
            c[tuple(cc)] = (d[tuple(hi)] - d[tuple(lo)]) / (2 * dx)
            comps.append(c)
        gv = np.stack(comps, -1)
        nrm = np.linalg.norm(gv, axis=-1)
        # 界面带：|∇d| 大 且 d 在零附近（用 |d| 小于带宽的中位数尺度）
        band = np.isfinite(nrm) & (nrm > 0)
        if region is not None:
            # 只在**变体-变体**的胞上（归档 region 给真值）
            m = band & (region > 0)
            mi = np.where(m)
            sel = (region[mi] == i) | (region[mi] == j)
            idx = tuple(a[sel] for a in mi)
        else:
            idx = np.where(band)
        if len(idx[0]) < 20:
            continue
        nh = gv[idx] / nrm[idx][:, None]
        # 只用 |d| 较小的胞（真正在界面上）
        dd = np.abs(d[idx])
        thr = np.percentile(dd, 30)
        keep = dd <= thr
        if keep.sum() < 20:
            continue
        nh = nh[keep]
        c2 = np.einsum('ni,i->n', nh, nj) ** 2
        out.append(c2)
        info.append((i, j, int(keep.sum())))
    if not out:
        return None, []
    return np.concatenate(out), info


def synth_plane(N, dx, nv, normal, ncmp, i=1, j=2):
    """合成一个法向为 `normal` 的平界面的稀疏 φ（两场），返回 (phi, region)。"""
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    c0 = np.array([N / 2, N / 2, N / 2]) * dx
    proj = (X - c0) @ (normal / np.linalg.norm(normal))
    phi = np.full((nv + 1, N, N, N), np.nan, np.float32)
    # 场 0 = 母相：远离；i 与 j 用 ∓proj
    phi[0] = 1e3
    phi[i] = np.where(np.abs(proj) <= 4 * dx, -proj, np.nan)
    phi[j] = np.where(np.abs(proj) <= 4 * dx, proj, np.nan)
    region = np.zeros((N, N, N), np.int8)
    region[proj > 0] = i
    region[proj <= 0] = j
    return phi, region


def main():
    print('=' * 108)
    print('_r195 —— 用**真实 φ**（`band_*` 稀疏带）重量 `c2p = (n̂·ncmp)²`')
    print('  ⚠ 更正 `§132.2`：归档快照**有**带内稀疏 φ（`band_*`），不是"没有 φ"')
    print('=' * 108)
    ncmp = load_ncmp()
    i, j = 1, 2
    nj = ncmp[j, i] / np.linalg.norm(ncmp[j, i])
    N, dx = 48, 1e-8

    # ---- C-2 正对照：法向 = ncmp ----
    print()
    print('  ## **C-2/C-3 合成对照**（同口径建基准）')
    phi, reg = synth_plane(N, dx, 2, nj, ncmp, i, j)
    c2, info = c2p_from_phi(phi, ncmp, dx, region=reg)
    med_p = float(np.median(c2)) if c2 is not None else float('nan')
    print('     平面 法向 = `ncmp` ⇒ `c2p` 中位 = **%.4f**（期望 1.0）%s'
          % (med_p, '✅' if abs(med_p - 1) < 0.02 else '❌'))
    rng = np.random.default_rng(11)
    meds = []
    for t in range(3):
        u = rng.standard_normal(3)
        u /= np.linalg.norm(u)
        ph, rg = synth_plane(N, dx, 2, u, ncmp, i, j)
        cc, _ = c2p_from_phi(ph, ncmp, dx, region=rg)
        if cc is not None:
            meds.append(float(np.median(cc)))
    null = float(np.mean(meds)) if meds else float('nan')
    print('     随机取向平面（3 个）⇒ `c2p` 中位 = %s ⇒ 平均 **%.4f**'
          % (['%.4f' % m for m in meds], null))
    print('     ⇒ ⚠ 与 `region` 重建不同，**真 φ 口径的零基准应接近 0.5**；'
          '实测 %.3f' % null)

    # ---- C-1 自洽正对照 + C-4 实测 ----
    print()
    print('  ## **C-1 自洽 + C-4 实测**：归档快照')
    for arm in ('saSet2', 'saOddG', 'mb2fp10', 'swN128', 'sgG', 't1N112L800'):
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            continue
        last = max(fs, key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1)))
        mf = os.path.join(d, 'meta.json')
        dxx = 62.5e-9
        if os.path.exists(mf):
            dxx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
        z = np.load(last, allow_pickle=True)
        if 'band_idx' not in z:
            print('     %-12s ⚠ 无 `band_*` ⇒ 跳过' % arm)
            continue
        phi = rebuild(z)
        if phi is None:
            print('     %-12s ⚠ 重建失败' % arm)
            continue
        reg = z['region'] if 'region' in z else None
        # C-1：重建 φ 的 argmin 是否复现 region（带内）
        c1 = '—'
        if reg is not None:
            full = np.where(np.isfinite(phi), phi, np.inf)
            am = np.argmin(full, 0)
            fin = np.isfinite(phi).any(0)
            if fin.any():
                agree = float((am[fin] == reg[fin]).mean())
                c1 = '%.4f（带内 %d 胞）' % (agree, int(fin.sum()))
        c2, info = c2p_from_phi(phi, ncmp, dxx, region=reg)
        if c2 is None:
            print('     %-12s step=%s ⚪ **不适用**（无可用变体-变体界面）'
                  % (arm, z['step'] if 'step' in z else '?'))
            continue
        q = np.percentile(c2, [10, 25, 50, 75, 90])
        med = float(np.median(c2))
        dev = (med - null) / null if null == null and null else float('nan')
        print('     %-12s step=%-5s 接触对 %-2d 用胞 %-7d **C-1 argmin 复现 region = %s**'
              % (arm, z['step'] if 'step' in z else '?', len(info), len(c2), c1))
        print('                  `c2p` 分位 [10/25/50/75/90] = %s ⇒ 中位 **%.3f**'
              % (np.array2string(q, precision=3), med))
        print('                  相对合成零基准 %.3f 偏离 **%+.1f%%** ⇒ %s'
              % (null, 100 * dev,
                 '**与随机取向无显著差别**' if abs(dev) < 0.15 else
                 ('**显著偏向不变平面**' if dev > 0 else '**显著偏离不变平面**')))
    print()
    print('  ⚠ 记账：真 φ 口径用**中心差分**，只在加号两侧邻居都有限时才算 ⇒ 带边缘自动排除。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
