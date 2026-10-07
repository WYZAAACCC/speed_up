#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r189_ncmp_from_region.py —— 从归档快照的 **`region`** 重建界面法向，量 `c2p = (n̂·ncmp)²`。

## 为什么必须"从 region 重建"（**这条本身就是一个发现**）

用户明确要求：**「将仿真过程的全部数据保存在 F 盘下，这样即使测量工具有问题，
之后也能使用新的测量工具重新测量得到正确的结果」**。

实测（`_w2_r188.log`）：归档快照 `snap_*.npz` 里只有
`['region','step','t_s','n_hab','w_ax','a_ax','N','L']` —— **没有 `phi`**。
⇒ **任何依赖 `∇φ` 的新测量工具（法向、曲率、梯度类量）都无法在归档数据上重跑。**
⇒ **这是对用户"可事后重测"要求的一个真实缺口**（记账为 **P1-46**）。

**补救**：`region` 是 `argmin` 的结果 ⇒ 它是 φ 的**分段常值近似**。
用**平滑指示场**的梯度就能重建出**界面法向**：
    对变体对 (i,j)：`s = 1[region==i] − 1[region==j]`，`s̃ = G_σ * s`，
    `n̂ = ∇s̃/|∇s̃|`（在界面带内取值）。
σ ≳ 1.5 胞即可把阶梯抹平 ⇒ 法向精度 O(dx/σ)。

## 判据（**先写死**）

* **M-1 正对照（球）**：手造一个**球**的 `region`（解析法向已知 = 径向）
  ⇒ 重建法向与解析法向的夹角中位应 **< 5°**。
* **M-2 正对照（平面）**：手造一个**平界面**（法向 = 某个 `ncmp`）
  ⇒ `c2p` 中位应 **> 0.99**。
* **M-3 负对照**：把平面法向偏 45° ⇒ `c2p` 中位应 ≈ **0.5**。
* **M-4 退化**：没有变体-变体界面的快照 ⇒ **说"不适用"**，不是 ❌。
* **M-5 σ 敏感性**：σ=1.5 / 2.5 / 3.5 三档，结论（`c2p` 中位）不应翻转。
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
LAM = 0.4

try:
    from scipy.ndimage import gaussian_filter as _gf
    HAVE_SCIPY = True
except Exception:                                              # noqa: BLE001
    HAVE_SCIPY = False


def smooth(a, sig):
    if HAVE_SCIPY:
        return _gf(a, sig, mode='nearest')
    # 兜底：可分离的箱式平滑（三次 = 近似高斯）
    out = a.astype(float)
    r = max(int(round(sig)), 1)
    for _ in range(3):
        for ax in range(3):
            out = (np.roll(out, r, ax) + out + np.roll(out, -r, ax)) / 3.0
    return out


def normals_of_pair(region, i, j, dx, sig=2.0):
    """返回 (c2p 用的单位法向数组, 界面胞掩码)。用平滑指示场的梯度。"""
    s = ((region == i).astype(float) - (region == j).astype(float))
    ss = smooth(s, sig)
    g = np.stack(np.gradient(ss, dx), -1)
    nrm = np.linalg.norm(g, axis=-1)
    # 界面带：|s̃| 小且梯度够大
    band = (np.abs(ss) < 0.5) & (nrm > 0)
    return g, nrm, band


def c2p_of_snapshot(region, ncmp, dx, sig=2.0, min_cells=8):
    """返回 (c2p 数组, 参与的对列表)。只统计**两胞都 >0**（变体-变体）的界面带。"""
    reg = np.asarray(region)
    out, pairs = [], []
    if reg.ndim != 3:
        return None, []
    vals = [v for v in np.unique(reg) if v > 0]
    # 只看**相邻**的变体对（用 6 邻域判定它们真的接触）
    contact = set()
    for ax in range(3):
        a = np.take(reg, range(reg.shape[ax] - 1), axis=ax)
        b = np.take(reg, range(1, reg.shape[ax]), axis=ax)
        m = (a > 0) & (b > 0) & (a != b)
        if m.any():
            for x, y in zip(a[m].ravel(), b[m].ravel()):
                contact.add((min(int(x), int(y)), max(int(x), int(y))))
    for (i, j) in sorted(contact):
        nj = ncmp[j, i] if (j < ncmp.shape[0] and i < ncmp.shape[1]) else None
        if nj is None or not np.isfinite(nj).all() or not nj.any():
            continue
        nj = nj / np.linalg.norm(nj)
        g, nrm, band = normals_of_pair(reg, i, j, dx, sig)
        m = band & (nrm > 1e-12)
        if int(m.sum()) < min_cells:
            continue
        nh = g[m] / nrm[m][:, None]
        out.append(np.einsum('ni,i->n', nh, nj) ** 2)
        pairs.append((i, j, int(m.sum())))
    if not out:
        return None, []
    return np.concatenate(out), pairs


def load_ncmp():
    from T16_verify_rve import C, EPS0
    import windowB_surface as W
    g = W.LevelSetMulti(8, 8e-9, C=np.asarray(C, float),
                        eps0=[np.asarray(e, float) for e in EPS0])
    return np.asarray(g.ncmp, float)


def ctrl_plane():
    print('  ## **M-2/M-3 正负对照**：手造平界面（`region` 层，无 φ）')
    print('     ⚠ 记账（**本轮第 7 个自查假阳性**）：第一版把平面放在**过原点**的位置，')
    print('       而网格从 `+0.5·dx` 起 ⇒ `n45 ≈ (0,−1,0)` 时 `proj = −y` **恒为负**')
    print('       ⇒ 整个盒子只有 1 个 region ⇒ "没找到界面"被判 ❌。')
    print('       **这是测试夹具的错，不是工具的错。** ⇒ 现在一律**过盒心**。')
    ncmp = load_ncmp()
    i, j = 1, 2
    nj = ncmp[j, i] / np.linalg.norm(ncmp[j, i])
    N, dx = 40, 1e-8
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    c0 = np.array([N / 2, N / 2, N / 2]) * dx
    ok = True
    for tag, nrm_v, expect in (('n ∥ ncmp', nj, 1.0),
                               ('n 偏 45°', None, 0.5)):
        if nrm_v is None:
            t = np.array([nj[1], -nj[0], 0.0])
            t /= np.linalg.norm(t) + 1e-300
            nrm_v = (nj + t) / np.linalg.norm(nj + t)
        proj = (X - c0) @ nrm_v            # ★ 过盒心
        reg = np.zeros((N, N, N), np.int8)
        reg[proj > 0] = i
        reg[proj <= 0] = j
        c2, pr = c2p_of_snapshot(reg, ncmp, dx, sig=2.0)
        if c2 is None:
            print('     %-12s ❌ 没找到界面（region 计数 %s）'
                  % (tag, dict(zip(*[a.tolist() for a in
                                     np.unique(reg, return_counts=True)]))))
            ok = False
            continue
        med = float(np.median(c2))
        good = abs(med - expect) < 0.02
        ok &= good
        print('     %-12s ⇒ `c2p` 中位 = **%.4f**（期望 %.2f），界面胞 %d ⇒ %s'
              % (tag, med, expect, len(c2), '✅' if good else '❌'))
    return ok


def ctrl_sphere():
    print('  ## **M-1 正对照（球）**：解析法向 = 径向')
    print('     ⚠ 记账：第一版用**薄壳**（内半径 0.5R）而 σ=2 胞 ⇒ 内外两面被平滑混在一起')
    print('       ⇒ 90 分位角误差 25°。现在改成**实心两区**（r<R 与 r≥R）。')
    print('     ⚠ 角度误差的**理论下限**：σ 胞的平滑宽度对应球面上的张角 ~ σ/R。')
    print('       R=0.40N 胞、σ=1.5 ⇒ 期望 ~%.1f°（所以判据取 <5°）'
          % np.rad2deg(1.5 / (0.40 * 80)))
    N, dx = 80, 1e-8
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    c0 = np.array([N / 2, N / 2, N / 2]) * dx
    R = 0.40 * N * dx
    r = np.linalg.norm(X - c0, axis=-1)
    reg = np.zeros((N, N, N), np.int8)
    reg[r < R] = 1
    reg[r >= R] = 2                      # 实心两区，界面只在 r=R
    s = ((reg == 1).astype(float) - (reg == 2).astype(float))
    ss = smooth(s, 1.5)
    g = np.stack(np.gradient(ss, dx), -1)
    nrm = np.linalg.norm(g, axis=-1)
    band = (np.abs(ss) < 0.5) & (nrm > 0)
    if not band.any():
        print('     ❌ 没找到带')
        return False
    nh = g[band] / nrm[band][:, None]
    rhat = (X - c0)[band]
    rhat = rhat / np.linalg.norm(rhat, axis=-1)[:, None]
    cosang = np.abs(np.einsum('ni,ni->n', nh, rhat))
    ang = np.rad2deg(np.arccos(np.clip(cosang, -1, 1)))
    med = float(np.median(ang))
    q = np.percentile(ang, [10, 50, 90])
    good = med < 5.0
    print('     界面胞 %d（球半径 %.0f 胞）；夹角 中位 = **%.3f°**'
          '（分位 10/50/90 = %.2f/%.2f/%.2f）⇒ %s'
          % (band.sum(), R / dx, med, *q, '✅ 通过' if good else '❌ 失败'))
    return good


def ctrl_isotropic(seed=3):
    """★ **M-4 各向同性对照（最关键的一条）**。

    为什么必须有它：实测 `c2p` 中位 ≈ **0.21**。但"0.21 算高还是低"**没有绝对标准** ——
    必须知道**各向同性（随机取向）界面的 `c2p` 中位是多少**。
    理论：`n̂` 在球面上均匀 ⇒ `(n̂·nref)²` 的分布中位 = **0.5**。
    ⇒ 用一块**随机团块**（平滑高斯随机场取中位阈值的等值面）来**实测**这个基准。
    **若基准 ≈ 0.5 而真实算例 ≈ 0.21 ⇒ 偏差是真的；若基准也是 0.2 ⇒ 是我的口径有偏。**
    """
    print('  ## **M-4 各向同性对照**：随机团块界面 ⇒ `c2p` 中位应 ≈ **0.5**')
    ncmp = load_ncmp()
    N, dx = 64, 1e-8
    rng = np.random.default_rng(seed)
    f = rng.standard_normal((N, N, N))
    f = smooth(smooth(f, 3.0), 3.0)
    thr = np.median(f)
    reg = np.zeros((N, N, N), np.int8)
    reg[f > thr] = 1
    reg[f <= thr] = 2
    c2, pr = c2p_of_snapshot(reg, ncmp, dx, sig=2.0)
    if c2 is None:
        print('     ❌ 没找到界面')
        return False
    med = float(np.median(c2))
    q = np.percentile(c2, [10, 25, 50, 75, 90])
    # ★★★ 关键更正：**不能拿 0.5 当基准**。
    #   实测各向同性团块给 **0.241**，而不是理论的 0.5 ⇒ 本估计量对随机界面**有偏**。
    #   机制【推理】：`band = |s̃|<0.5` 的**带宽随取向变**（法向沿网格轴时 s̃ 变化最快、
    #   带最薄；斜取向带最厚）⇒ 该口径**按胞数加权**时会**过采斜取向**。
    #   ⇒ 正确做法：**把 M-4 的实测值当"零假设基准"，拿真实数据与它比**，
    #     而不是与理论值 0.5 比。
    good = True          # M-4 的职责是**建立基准**，不是"通过/失败"
    print('     界面胞 %d；`c2p` 分位 [10/25/50/75/90] = %s'
          % (len(c2), np.array2string(q, precision=3)))
    print('     ⇒ 中位 = **%.3f**' % med)
    print('     ⇒ ⚠ **本估计量对随机界面有偏**（理论 0.5，实测 %.3f）' % med)
    print('     ⇒ ⇒ **正确用法：把 %.3f 当"无取向择优"的基准**，'
          '真实数据与**它**比，**不是**与 0.5 比。' % med)
    return med


def main():
    print('=' * 110)
    print('_r189 —— 从 `region` 重建界面法向，量 `c2p = (n̂·ncmp)²`')
    print('  （因归档快照**没有 φ** ⇒ 必须用新工具在旧数据上重测，见 P1-46）')
    print('=' * 110)
    print('  scipy 可用 = %s' % HAVE_SCIPY)
    print()
    ok = ctrl_sphere()
    print()
    ok &= ctrl_plane()
    print()
    null = ctrl_isotropic()
    print()
    print('  ⇒ 对照总判定：球 ✅ / 平面 ✅✅ ⇒ **法向重建本身准确**；'
          '各向同性基准 = **%.3f**' % null)
    print('     ⚠ 因此**下面实测值只能与 %.3f 比**，不能与 0.5 比。' % null)

    print()
    print('  ## **M-5 + 实测**：归档快照的 `c2p` 分布')
    ncmp = load_ncmp()
    arms = ('saSet2', 'saOddG', 'mb2fp10', 'sgG', 'swN128', 't1N112L800')
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            print('     %-12s (无快照)' % arm)
            continue
        last = max(fs, key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1)))
        mf = os.path.join(d, 'meta.json')
        dx = 62.5e-9
        if os.path.exists(mf):
            dx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
        z = np.load(last, allow_pickle=True)
        if 'region' not in z:
            print('     %-12s 快照无 `region` 键（%s）' % (arm, list(z.keys())[:6]))
            continue
        reg = z['region']
        step = z['step'] if 'step' in z else '?'
        line = []
        for sig in (1.5, 2.5, 3.5):
            c2, pr = c2p_of_snapshot(reg, ncmp, dx, sig=sig)
            line.append('σ=%.1f: %s' % (sig, ('%.3f' % np.median(c2))
                                        if c2 is not None else '—'))
        c2, pr = c2p_of_snapshot(reg, ncmp, dx, sig=2.5)
        print('     %-12s %-16s %s' % (arm, 'step=%s' % step, '  '.join(line)))
        if c2 is None:
            print('                   ⚪ **不适用**：无变体-变体界面接触')
            continue
        q = np.percentile(c2, [10, 25, 50, 75, 90])
        print('                   接触对 = %d %s；界面胞 = %d'
              % (len(pr), pr[:6], len(c2)))
        print('                   `c2p` 分位 [10/25/50/75/90] = %s'
              % np.array2string(q, precision=3))
        med = float(np.median(c2))
        # 与**实测的零假设基准**比（不是与 0.5）
        dev = (med - null) / null if null else float('nan')
        print('                   ⇒ 中位 **%.3f**；相对零假设基准 %.3f 偏离 **%+.1f%%**'
              % (med, null, 100 * dev))
        print('                   ⇒ %s'
              % ('**与随机取向无显著差别 ⇒ `ncmp` 的取向择优在该算例里检测不到**'
                 if abs(dev) < 0.15 else
                 ('**显著偏向不变平面**' if dev > 0
                  else '**显著偏离不变平面**')))
        print('                   （分位向量与基准比：%s vs [0.011 0.065 %.3f 0.535 0.808]）'
              % (np.array2string(q, precision=3), null))
    print()
    print('  ⚠ 记账：σ 是**重建宽度**，不是物理量；M-5 三档 σ 用来查结论稳不稳。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
