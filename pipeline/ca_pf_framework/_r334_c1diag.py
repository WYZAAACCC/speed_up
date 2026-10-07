#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r334_c1diag.py —— ★ 查清 Q-15 的阻塞点：`_r195` 的 **C-1 自洽对照**为什么只有 0.806–0.933。

## 这是一个**测量工具的测量工具**（硬规则 ④：判据先过正对照）

`_r195` 用 `band_*`（带内稀疏 φ）重建 φ，然后要求
`argmin_k φ_k` 复现归档 `region`，判据写的是「**带内逐位相同**」，
实测只有 **0.806–0.933** ⇒ 工具没自证 ⇒ `§134.2` 的 `c2p` 数字作废。

**本脚本要回答的是**：这个 ❌ 是
  (a) **我的重建/掩码写错了**（第 30 个自查错误），还是
  (b) **归档里 `region` 与 `phi` 真的不一致**（那是**代码**的问题，性质严重）。

## 掩码为什么可疑（**先验推理，必须实测**）

`_r195:218` 用的是 `fin = np.isfinite(phi).any(0)`
= 「**至少一个场**在这个胞上把 φ 存下来了」。

但 `_sparse_band` 的判据是 `|φ_k| ≤ B·Δx`（`B = phi_band_cells`）——**对称**的：
一个胞若离 k 的界面 **> B 个胞**，则 φ_k **不存**（无论正负）。于是：

* **不在 k 的带里** ⇒ `|φ_k| > BΔx`；
* 若该胞**在某个 `m` 的带里**且 `φ_m` 是**存下来的最小值** ⇒ 看似 `argmin = m`；
* 但**没存下来的 `k`** 完全可能是**真的 argmin**（只要 φ_k < φ_m）——
  填 `+inf` 就把它**当成"无穷大"**，即**默认"没存 ⇒ 不是最小"**。**这个默认是错的。**

**严格（数学上必须为真）的掩码** `R`：
> `R = { 所有场都存下来的胞 } ∪ { 存下来的最小值 < 0 的胞 }`

理由：若 `φ_m < 0`，则胞在 m **内部** ⇒ 任何 `j ≠ m` 的 φ_j > 0（SDF 性质）
⇒ 未存的 j 满足 `φ_j > BΔx > φ_m` ⇒ `m` **就是**全局 argmin。
若所有场都存下来，则"存下来的 argmin"**就是**全局 argmin。
⇒ **在 `R` 上，argmin 必须 100% 等于 region**；`R` 上的任何不符**都不是掩码的错**。

## 判据（**先写死**）

* **P-0 正对照（合成）**：造一个已知 φ（两/三区域、球+平面）⇒ `_sparse_band`（**真代码**，
  用 `ast` 从 `_bk_exp.py` 抽出源码执行，**不用副本**）⇒ `rebuild` ⇒
  `R` 上的符合率必须 **= 1.0000**。**不过就停，不出任何真实数据结论。**
* **P-1 负对照（合成）**：把重建里的 `+inf` 换成 `0`（一个**已知错误**的解码）
  ⇒ `R` 上符合率必须 **< 1**（证明本判据**有分辨力**，不是永远给 1）。
* **R-1 真实数据·严格掩码**：`R` 上符合率。**1.0000 ⇒ 工具没错、归档自洽**，Q-15 解锁。
* **R-2 真实数据·旧掩码**：`any(0)` 上符合率 ⇒ **应当复现 0.806–0.933**（复现 = 确证诊断对象）。
* **R-3 不符胞的解剖**：不符胞到最近 region 边界的**胞距**分布 + `(argmin, region)` 配对计数
  + 「region 那个场本身存没存下来」。

**⚠ 硬规则 ⑯**：P-0 不过 ⇒ 本脚本其余输出**全部作废**，不得解读。
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')


# --------------------------------------------------------------------------- #
# 真·编码器：从 `_bk_exp.py` 抽源码执行（**不是副本**，防止漂移）
# --------------------------------------------------------------------------- #
def load_real_sparse_band():
    path = os.path.join(HERE, '_bk_exp.py')
    src = open(path, encoding='utf-8').read()
    tree = ast.parse(src)
    fn = None
    for nd in tree.body:
        if isinstance(nd, ast.FunctionDef) and nd.name == '_sparse_band':
            fn = nd
            break
    if fn is None:
        raise RuntimeError('在 _bk_exp.py 里找不到 _sparse_band')
    mod = ast.Module(body=[fn], type_ignores=[])
    ns = {'np': np}
    exec(compile(mod, path, 'exec'), ns)
    return ns['_sparse_band']


# --------------------------------------------------------------------------- #
# 被测解码器：与 `_r195:rebuild` **逐字相同**
# --------------------------------------------------------------------------- #
def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    fld = z['band_fld'].astype(int)
    idx = z['band_idx'].astype(int)
    val = z['band_val'].astype(np.float32)
    flat[fld, idx] = val
    return phi


def rebuild_broken(z, fill=0.0):
    """P-1 负对照：把带外的填充从 `+inf` 换成 `fill`（一个已知错误的解码）。"""
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), fill, np.float32)
    flat = phi.reshape(nf, -1)
    fld = z['band_fld'].astype(int)
    idx = z['band_idx'].astype(int)
    flat[fld, idx] = z['band_val'].astype(np.float32)
    return phi


# --------------------------------------------------------------------------- #
# 三个掩码上的符合率
# --------------------------------------------------------------------------- #
def masks_and_argmin(phi, band_cells, dx):
    fin = np.isfinite(phi)
    any_ = fin.any(0)
    all_ = fin.all(0)
    full = np.where(fin, phi, np.inf)
    am = np.argmin(full, 0)
    minval = np.min(full, 0)
    strict = all_ | (minval < 0.0)
    return am, dict(any=any_, all=all_, strict=strict, minval=minval, fin=fin)


def agree(am, reg, mask):
    if not mask.any():
        return float('nan'), 0
    return float((am[mask] == reg[mask]).mean()), int(mask.sum())


# --------------------------------------------------------------------------- #
# P-0 合成正对照
# --------------------------------------------------------------------------- #
def synth(N, dx, nf, seed=11, kind='sphere'):
    """造一个**已知且自洽**的 φ：(nf, N, N, N)，场 k 的 φ_k = 到区域 k 的带符号距离。

    做法：先给每个胞指派一个区域（真值），再算每个区域的**欧氏距离场**，
    区域内取负。用 `region` 的 6-邻域边界反推不现实 ⇒ 用**构造式**：
    区域 = 按一个随机单位向量 u 分层的**平行板条**（层厚不等），
    距离用 `|proj − 层中心|` 的近似（对平行板条**就是精确** SDF）。
    """
    rng = np.random.default_rng(seed)
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    u = rng.standard_normal(3)
    u /= np.linalg.norm(u)
    proj = (X @ u - (X[0, 0, 0] @ u))
    # 把 proj 分成 nf 条（不等厚）
    span = float(proj.max())
    cuts = np.sort(rng.uniform(0.15, 0.85, max(nf - 1, 0))) * span
    edges = np.concatenate([[0.0], cuts, [span]])
    reg = np.full(proj.shape, nf - 1, np.int8)
    for k in range(nf - 1):
        reg[(proj >= edges[k]) & (proj < edges[k + 1])] = k
    # φ_k = 带符号距离（对平行板条精确）：到区域 k 的最近边界
    phi = np.full((nf,) + proj.shape, np.nan, np.float32)
    for k in range(nf):
        # 区域 k 的上下界（沿 u）：对平行板条，
        #   φ_k = max(lo − proj, proj − hi)  就是**精确**的带符号距离
        #   ⚠ 第一版在这里多写了 `np.maximum(..., 0.0)` ⇒ 板条内部被压成 0 ⇒
        #     P-0 的 `strict` 掩码变成**空集**（0 胞）而被正对照当场抓住。
        lo, hi = edges[k], edges[k + 1]
        phi[k] = np.maximum(lo - proj, proj - hi)
    return phi, reg


def main():
    print('=' * 108)
    print('_r334 —— C-1 为什么只有 0.806–0.933？（Q-15 阻塞点）')
    print('=' * 108)
    sparse_band = load_real_sparse_band()
    print('  ✅ 已从 `_bk_exp.py` 抽取**真** `_sparse_band`（ast 源码，非副本）')

    N = 48
    dx = 1e-8
    B = 6

    # ---------------- P-0 正对照（合成） ----------------
    print()
    print('  ## **P-0 合成正对照**（φ 已知且自洽 ⇒ 掩码判据必须成立）')
    phi_s, reg_s = synth(N, dx, 5, seed=11)
    z = sparse_band(phi_s, dx, B)
    z = dict(z)
    z['N'] = np.int64(N)
    p0 = rebuild(z)
    am, mk = masks_and_argmin(p0, B, dx)
    a_any, n_any = agree(am, reg_s, mk['any'])
    a_all, n_all = agree(am, reg_s, mk['all'])
    a_str, n_str = agree(am, reg_s, mk['strict'])
    print('     掩码 `any(0)`  : 符合率 = %.4f（%d 胞）' % (a_any, n_any))
    print('     掩码 `all(0)`  : 符合率 = %.4f（%d 胞）' % (a_all, n_all))
    print('     掩码 **严格 R** : 符合率 = **%.4f**（%d 胞）%s'
          % (a_str, n_str, '✅' if abs(a_str - 1.0) < 1e-12 else '❌ P-0 不过 ⇒ 停'))
    if not (abs(a_str - 1.0) < 1e-12):
        print('     ⇒ ❌ **P-0 未通过**：本脚本其余输出全部作废（硬规则 ⑯）。')
        return 2

    # ---------------- P-1 负对照：已知错误的解码 ----------------
    pb = rebuild_broken(z, fill=0.0)
    amb, mkb = masks_and_argmin(pb, B, dx)
    a_str_b, n_str_b = agree(amb, reg_s, mkb['strict'])
    print('     **P-1 负对照**（带外填 `0` 代替 `+inf`）：严格 R 符合率 = %.4f（%d 胞）%s'
          % (a_str_b, n_str_b,
             '✅ 判据有分辨力' if a_str_b < 1.0 else '❌ 判据无分辨力 ⇒ 全体作废'))
    if not (a_str_b < 1.0):
        return 2

    # ---------------- 真实数据 ----------------
    print()
    print('  ## **R-1/R-2/R-3 真实归档**')
    arms = sys.argv[1:] or ['saSet2', 'saOddG', 'mb2fp10', 'swN128', 'sgG', 't1N112L800']
    for arm in arms:
        d = os.path.join(MB, 'dry_' + arm)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not fs:
            print('     %-12s ⚠ 无快照' % arm)
            continue
        last = max(fs, key=lambda f: int(re.search(r'_(\d+)\.npz$', f).group(1)))
        dxx = 62.5e-9
        mf = os.path.join(d, 'meta.json')
        if os.path.exists(mf):
            dxx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
        zz = np.load(last, allow_pickle=True)
        if 'band_idx' not in zz:
            print('     %-12s ⚠ 无 `band_*`' % arm)
            continue
        reg = np.asarray(zz['region'], np.int64)
        p = rebuild(zz)
        nf = p.shape[0]
        nn = int(zz['N'])
        bc = int(zz['band_cells'])
        am, mk = masks_and_argmin(p, bc, dxx)
        a_any, n_any = agree(am, reg, mk['any'])
        a_all, n_all = agree(am, reg, mk['all'])
        a_str, n_str = agree(am, reg, mk['strict'])
        print()
        print('     ### %-12s step=%-5s nf=%-3d N=%-5d B=%d  存胞=%d（%.3f%% of %d）'
              % (arm, zz['step'], nf, nn, bc,
                 int(zz['band_val'].size),
                 100.0 * zz['band_val'].size / float(nn ** 3), nn ** 3))
        print('        R-2 旧掩码 `any(0)` 符合率 = **%.4f**（%d 胞）'
              % (a_any, n_any))
        print('        R-1 **严格掩码 R** 符合率 = **%.4f**（%d 胞）%s'
              % (a_str, n_str, '✅ 归档自洽' if abs(a_str - 1.0) < 1e-12 else '❌ 真不一致'))
        print('        （参考 `all(0)` 符合率 = %.4f，%d 胞）' % (a_all, n_all))

        # ---- R-3 不符胞解剖（在旧掩码上）----
        bad = mk['any'] & (am != reg)
        nb = int(bad.sum())
        if nb == 0:
            print('        R-3：旧掩码上**无不符** ⇒ 不可解剖')
            continue
        # region 那个场本身存没存下来
        finz = mk['fin']
        regc = np.clip(reg, 0, nf - 1)
        stored_reg = finz[regc, np.arange(nn)[:, None, None],
                          np.arange(nn)[None, :, None],
                          np.arange(nn)[None, None, :]][bad]
        print('        R-3 不符胞 %d：其中 **region 的场自己没存** 的占 **%.1f%%**'
              % (nb, 100.0 * float((~stored_reg).mean())))
        # 到最近 region 边界的胞距（迭代膨胀）
        bnd = np.zeros((nn, nn, nn), bool)
        for ax in range(3):
            bnd |= (reg != np.roll(reg, 1, ax)) | (reg != np.roll(reg, -1, ax))
        cur = bnd.copy()
        dist = np.full((nn, nn, nn), 999, np.int32)
        dist[cur] = 0
        for step in range(1, 13):
            nxt = cur.copy()
            for ax in range(3):
                nxt |= np.roll(cur, 1, ax) | np.roll(cur, -1, ax)
            new = nxt & ~cur
            dist[new] = step
            cur = nxt
        dv = dist[bad]
        hh = np.bincount(dv[dv < 999], minlength=13)[:10]
        print('        到最近 region 边界的胞距直方图 [0..9] = %s' % hh.tolist())
        # 配对计数（top）
        pairs = {}
        ai = am[bad].astype(int)
        ri = reg[bad].astype(int)
        for a_, r_ in zip(ai.tolist(), ri.tolist()):
            pairs[(a_, r_)] = pairs.get((a_, r_), 0) + 1
        top = sorted(pairs.items(), key=lambda kv: -kv[1])[:6]
        print('        (argmin, region) top = %s' % (top,))
        # 若"region 的场自己没存"占比 = 100%，则不符**完全**由掩码造成（≈ 我的错）
        if abs(float((~stored_reg).mean()) - 1.0) < 1e-12:
            print('        ⇒ **100% 的不符胞都满足「region 的场没存」** '
                  '⇒ 不符**完全**由掩码 `any(0)` 造成（我的工具错），**不是**归档不自洽。')
        else:
            print('        ⇒ ⚠ 存在「region 的场**存了**却仍不符」的胞 ⇒ '
                  '**归档 `region` 与 `phi` 可能真不一致**，需单独定案。')

    print()
    print('  ⚠ 记账：`R` 的成立依赖「φ_k 是到区域 k 的带符号距离且区域互斥」这一 SDF 性质；')
    print('     若引擎的 φ **不是** SDF（只保证符号/零集），`R` 上的不符就**不能**直接定罪归档。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
