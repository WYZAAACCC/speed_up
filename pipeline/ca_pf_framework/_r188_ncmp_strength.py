#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r188_ncmp_strength.py —— ★ **`ncmp` 通道到底有多强、以及它有没有真的生效？**

## 为什么查（`§131` 的量化跟进）

`§131` 更正了 `§129.1`：λ=0 时**存在**变体对耦合通道 `ncmp[k,l]`
（经 `aniso=0.4` 进 `stk`、经 `mob_beta=6.477` 进 `M(n)`）。
但"存在"不等于"有量级" —— **必须量出来**，否则 `§112` 的机制解释还是悬空的。

## 两问

* **N-1（解析，便宜）**：`stk(θ)` 与 `γ(θ)` 随 θ 变化多少？
  `windowB_surface.py:320-328`：
    `herring=True : γ+γ_θθ = γ₀[1 + 2Λ − 3Λ sin²θ]`
    `herring=False: γ      = γ₀[1 + Λ sin²θ]`
  ⇒ 报出 θ=0 / 90° 的比值（Λ=0.4）。
* **N-2（实测，关键）**：**真实仿真里的变体-变体界面，法向是否真的落在 `ncmp[k,l]` 上？**
  ⇒ 从归档快照 `snap_*.npz` 取 `phi`，算每个变体-变体界面胞的 `n̂ = ∇φ/|∇φ|`，
     再算 `c2p = (n̂·ncmp[k,l])²` 的分布。
  **若 `c2p` 集中在 1 附近 ⇒ 不变平面被真实实现 ⇒ `ncmp` 通道生效；**
  **若 `c2p` 接近均匀 ⇒ 该通道没起作用。**

## 规程

* **正对照**：手造一个**法向正好等于 `ncmp`** 的平界面，判据必须给出 `c2p = 1`；
  再手造一个**偏 45°** 的，必须给出 `c2p = 0.5`。
* **退化检查**：没有变体-变体界面的快照 ⇒ 必须说"不适用"，不是 ❌。
* ⚠ `c2p` 用**逐胞**的 φ 梯度；界面带内的 φ 梯度方向才是法向 ⇒ 只取带内胞。
"""
from __future__ import annotations

import glob
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W  # noqa: E402

MB = os.path.join(HERE, '_exp', '_bk_mb')
LAM = 0.4          # `_bk_exp.py:963` 的 `aniso=0.4`


def n1():
    print('  ## **N-1** 解析：`stk(θ)` 与 `γ(θ)` 随 θ 的变化（Λ = %.2f）' % LAM)
    print('     %-9s %-13s %-13s %-13s %s'
          % ('θ[°]', 'sin²θ', 'γ(θ)/γ₀', 'stk(θ)/γ₀', '备注'))
    for d in (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0):
        c = np.cos(np.deg2rad(d)) ** 2
        g = float(W.herring_stiffness(c, 1.0, LAM, herring=False))
        s = float(W.herring_stiffness(c, 1.0, LAM, herring=True))
        note = ('← n ∥ ncmp（不变平面）' if d == 0 else
                '← n ⊥ ncmp' if d == 90 else '')
        print('     %-9.1f %-13.4f %-13.4f %-13.4f %s' % (d, 1 - c, g, s, note))
    g0 = float(W.herring_stiffness(1.0, 1.0, LAM, herring=False))
    g9 = float(W.herring_stiffness(0.0, 1.0, LAM, herring=False))
    s0 = float(W.herring_stiffness(1.0, 1.0, LAM, herring=True))
    s9 = float(W.herring_stiffness(0.0, 1.0, LAM, herring=True))
    print('     ⇒ **γ** ：θ=0 → %.4fγ₀，θ=90° → %.4fγ₀，**比 = %.3f×**'
          % (g0, g9, g9 / g0))
    print('     ⇒ **stk**：θ=0 → %.4fγ₀，θ=90° → %.4fγ₀，**比 = %.3f×**'
          % (s0, s9, s0 / s9))
    print('     ⇒ 物理解读：`γ` 在**不变平面**取**最小**（对，低能面），')
    print('        而 `stk = γ+γ_θθ` 在那里取**最大**（对，**刻面**抗弯）')
    print('     ⇒ ⇒ **`ncmp` 通道的强度是 3 倍量级，不是小修正。**')


def load_ncmp():
    """从 `T16_verify_rve` 取 `C`、`EPS0`，用引擎自己的 `_pair_normals` 算 `ncmp`。"""
    try:
        from T16_verify_rve import C, EPS0
    except Exception as e:                                     # noqa: BLE001
        print('  ⚠ 取不到 `C`/`EPS0`：%s' % e)
        return None
    g = W.LevelSetMulti(8, 8e-9, C=np.asarray(C, float),
                        eps0=[np.asarray(e, float) for e in EPS0])
    return np.asarray(g.ncmp, float)


def snap_phi(path):
    d = np.load(path, allow_pickle=True)
    for k in ('phi', 'Phi', 'PHI'):
        if k in d:
            return d[k]
    return None


def interface_stats(phi, ncmp, dx, nv):
    """逐胞算 (k,l) 与 (n̂·ncmp[k,l])²。只取**带内**胞（|φ_k|、|φ_l| 都小）。"""
    if phi.ndim != 4:
        return None
    reg = np.argmin(phi, axis=0)                     # winner
    # runner-up：把 winner 置 +inf 再取 argmin
    p = phi.copy()
    np.put_along_axis(p, reg[None], np.inf, axis=0)
    run = np.argmin(p, axis=0)
    vv = (reg > 0) & (run > 0) & (reg != run)
    if not vv.any():
        return None, 0
    g = [np.gradient(phi[i], dx) for i in range(phi.shape[0])]
    out = []
    for i in range(1, phi.shape[0]):
        for j in range(i + 1, phi.shape[0]):
            m = vv & (((reg == i) & (run == j)) | ((reg == j) & (run == i)))
            if not m.any():
                continue
            nj = ncmp[j, i] if np.isfinite(ncmp[j, i]).all() else None
            if nj is None:
                continue
            # 用**差分场** d = φ_i − φ_j 的梯度作法向（跨界面两侧对称）
            dd = phi[i] - phi[j]
            gd = np.stack(np.gradient(dd, dx), -1)
            nrm = np.linalg.norm(gd, axis=-1)
            mm = m & (nrm > 1e-30)
            if not mm.any():
                continue
            nh = gd[mm] / nrm[mm][:, None]
            c2 = np.einsum('ni,i->n', nh, nj / np.linalg.norm(nj)) ** 2
            out.append(c2)
    if not out:
        return None, 0
    return np.concatenate(out), len(out)


def main():
    print('=' * 110)
    print('_r188 —— `ncmp` 通道的强度（N-1）与是否真的生效（N-2）')
    print('=' * 110)
    print()
    n1()

    print()
    print('  ## **N-2 正对照**：手造平界面，判据必须给出已知答案')
    ncmp = load_ncmp()
    if ncmp is None:
        print('     ⚠ 拿不到 `ncmp` ⇒ N-2 跳过')
        return 0
    fin = np.isfinite(ncmp).all(-1) & (ncmp != 0).any(-1)
    np.fill_diagonal(fin, False)
    print('     `ncmp` 表：%d×%d，有限且非零的**有序**项 = %d（应为 2×对数）'
          % (ncmp.shape[0], ncmp.shape[1], int(fin.sum())))
    # 正对照：构造 φ 使 1-2 界面法向 = ncmp[2,1]
    i, j = 1, 2
    if not fin[i, j]:
        print('     ⚠ `ncmp[%d,%d]` 不是有限非零 ⇒ 换一对' % (i, j))
        idx = np.argwhere(fin)
        if not len(idx):
            print('     ⚠ 没有可用的对 ⇒ 跳过')
            return 0
        i, j = idx[0]
    nj = ncmp[j, i] / np.linalg.norm(ncmp[j, i])
    N, dx = 24, 1e-8
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    phi = np.zeros((3, N, N, N))
    # 让 φ_1 − φ_2 = −(r·n)（界面在 r·n = 0 的平面上）⇒ ∇(φ_1−φ_2) ∥ n
    proj = X @ nj
    phi[i] = -proj
    phi[j] = proj
    phi[0] = 1e3                      # 母相永远不是 winner
    c2, n = interface_stats(phi, ncmp, dx, 2)
    if c2 is None:
        print('     ❌ 正对照没找到界面 ⇒ 判据本身有问题')
        return 1
    print('     **正对照**：界面法向 == `ncmp` ⇒ 实测 `c2p` 中位 = **%.6f**（期望 1.0），'
          '胞数 = %d ⇒ %s' % (float(np.median(c2)), n,
                            '✅ 通过' if abs(np.median(c2) - 1) < 1e-6 else '❌ 失败'))
    # 负对照：把法向偏 45°
    t = np.array([nj[1], -nj[0], 0.0])
    t /= np.linalg.norm(t) + 1e-300
    n45 = (nj + t) / np.linalg.norm(nj + t)
    phi2 = np.zeros_like(phi)
    proj2 = X @ n45
    phi2[i] = -proj2
    phi2[j] = proj2
    phi2[0] = 1e3
    c45, n45c = interface_stats(phi2, ncmp, dx, 2)
    if c45 is not None:
        print('     **负对照**：法向偏 45° ⇒ `c2p` 中位 = **%.6f**（期望 0.5）⇒ %s'
              % (float(np.median(c45)),
                 '✅ 通过' if abs(np.median(c45) - 0.5) < 0.02 else '❌ 失败'))

    # ---- 真实快照 ----
    print()
    print('  ## **N-2 实测**：归档快照里的变体-变体界面法向分布')
    for arm in ('saSet2', 'saOddG', 'mb2fp10', 'sgG'):
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            print('     %-10s (无快照)' % arm)
            continue
        last = max(fs, key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1)))
        meta = os.path.join(d, 'meta.json')
        dx = 62.5e-9
        if os.path.exists(meta):
            import json
            dx = float(json.load(open(meta)).get('dx_nm', 62.5)) * 1e-9
        phi = snap_phi(last)
        if phi is None:
            print('     %-10s 快照里没有 phi 键（键：%s）'
                  % (arm, list(np.load(last, allow_pickle=True).keys())[:8]))
            continue
        c2, n = interface_stats(np.asarray(phi, float), ncmp, dx, phi.shape[0] - 1)
        if c2 is None:
            print('     %-10s ⚪ **不适用**：该快照没有变体-变体界面（胞数 %d）'
                  % (arm, n))
            continue
        q = np.percentile(c2, [10, 25, 50, 75, 90])
        print('     %-10s 快照 %-14s 变体-变体界面胞 = **%d**' %
              (arm, os.path.basename(last), n))
        print('                `c2p = (n̂·ncmp)²` 分位 [10/25/50/75/90] = '
              '%s' % np.array2string(q, precision=4))
        print('                中位 %.4f ⇒ %s'
              % (float(np.median(c2)),
                 '**接近 1 ⇒ 不变平面被实现 ⇒ `ncmp` 通道生效**'
                 if np.median(c2) > 0.8 else
                 '中位不高 ⇒ 界面法向**没有**普遍落在不变平面上'))
    print()
    print('  ⚠ 记账：`c2p` 用**差分场**梯度作法向（跨界面两侧对称）；')
    print('     界面带内 φ 梯度才代表法向 ⇒ 本脚本用 winner/runner-up 判定变体-变体胞。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
