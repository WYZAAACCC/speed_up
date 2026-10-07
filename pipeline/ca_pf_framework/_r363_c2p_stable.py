#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r363_c2p_stable.py —— ★★★ Q-15：给 `c2p=(n̂·ncmp)²` 造一个**稳定且有理论值**的零基准。

## 为什么必须重造（`§168.5` R-2）

`_r195` 的零基准（C-3）给出 `['0.2622','0.0359','0.2211']` —— **散布 7 倍**，且 0.036 明显是坏的。
它用"随机取向平界面"、每个取向只取**很少的胞**、还叠了 `|d| ≤ 30 分位` 的二次筛选
⇒ 样本小 + 栅格阶梯效应 ⇒ 中位数散得离谱。**⇒ 那样的零基准上判不了 Q-15。**

## 本版怎么修：**用有理论值的合成对象**

* **C-2 已知答案**：合成一个法向**恰好等于** `ncmp[1,2]` 的平界面 ⇒ `c2p` 必须 = **1.0000**。
* **C-3′ 理论零基准（★ 关键改进）**：合成一个**球**。球的法向在球面上**均匀覆盖所有取向**
  ⇒ 对均匀取向，@@\\mathbb E[\\cos^2\\theta]=\\tfrac13@@ ⇒ **零基准有理论值 1/3**，
  而不再是"测出来一个数"。一个球给**上万胞** ⇒ 抽样噪声小、且**没有平界面那种栅格取向依赖**。
* **C-3″ 平界面对照**：仍跑若干随机取向平界面，**逐取向报样本数**，
  并给出**合并**后的均值与标准误 ⇒ 展示"合并"如何消除原来的 7 倍散布。
* **C-4 实测**：`saSet2` step 400 的 **F2 胞**上，法向取
  @@\\nabla(\\phi_k-\\phi_l)@@（**与 `advance` 同一个量**，`:3161`），
  与 `ncmp[k,l]` 比 ⇒ 与零基准 1/3 比。
* **判据**：C-4 显著 > 1/3 ⇒ 界面法向**偏向不变平面**（`ncmp` 生效）；≈1/3 ⇒ 不生效。
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
TH = 1.0 / 3.0


def load_ncmp():
    from T16_verify_rve import C, EPS0
    import windowB_surface as W
    g = W.LevelSetMulti(8, 8e-9, C=np.asarray(C, float),
                        eps0=[np.asarray(e, float) for e in EPS0])
    return np.asarray(g.ncmp, float)


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def c2p_from_dfield(d, nj, dx, extra=None):
    """法向取 `∇d`（中心差分，要求三向邻居都有限）。返回 (c2p 数组, 用胞数)。

    `extra`：可选的附加掩码（例如"只取 |d| ≤ 1Δx 的**真界面胞**"）。
    ⚠ **第 38 个自查错误**：第一版**没有** `extra` ⇒ 在 `d = φ_a − φ_b` 有限的**整片**
      （两个带的重叠区）上取平均，而那里**大部分胞并不是 a–b 界面**
      ⇒ 测出来的 0.356 是"界面胞 + 非界面胞"的混合（分位 1.7e-4 … 0.996，双峰）
      ⇒ 会给出**假阳性**。
    """
    N = d.shape[0]
    comps = []
    ok = np.zeros(d.shape, bool)
    ok[1:-1, 1:-1, 1:-1] = True
    for ax in range(3):
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        cc = [slice(None)] * 3
        lo[ax] = slice(0, N - 2)
        hi[ax] = slice(2, N)
        cc[ax] = slice(1, N - 1)
        c = np.full(d.shape, np.nan)
        c[tuple(cc)] = (d[tuple(hi)] - d[tuple(lo)]) / (2 * dx)
        comps.append(c)
        ok &= np.isfinite(c)
    gv = np.stack(comps, -1)
    nrm = np.linalg.norm(gv, axis=-1)
    ok &= nrm > 0
    if extra is not None:
        ok &= extra
    if not ok.any():
        return np.zeros(0), 0
    nh = gv[ok] / nrm[ok][:, None]
    return (nh @ nj) ** 2, int(ok.sum())


def synth_sphere(N, dx, k, l, R_frac=0.32):
    """两区域球：场 k 在球内（φ<0），场 l 在外；返回 d = φ_k − φ_l。"""
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    c0 = 0.5 * N * dx
    r = np.linalg.norm(X - c0, axis=-1)
    R = R_frac * N * dx
    sdf = r - R
    return sdf          # φ_k = sdf, φ_l = −sdf ⇒ d = 2·sdf（法向 = 径向 ⇒ 各向均匀）


def main():
    print('=' * 104)
    print('_r363 —— `c2p` 的**稳定零基准**（含理论值 1/3）⇒ 回答 Q-15')
    print('=' * 104)
    ncmp = load_ncmp()
    i, j = 1, 2
    nj = ncmp[j, i] / np.linalg.norm(ncmp[j, i])
    print('  ncmp[%d,%d] = %s（已归一化）' % (j, i, np.array2string(nj, precision=4)))

    N = 96
    dx = 1e-8

    # ---- C-2 已知答案：平界面，法向恰好 = ncmp ----
    x = (np.arange(N) + 0.5) * dx
    X = np.stack(np.meshgrid(x, x, x, indexing='ij'), -1)
    proj = (X - 0.5 * N * dx) @ nj
    d2 = 2.0 * proj               # φ_k−φ_l 的零集 = 中面，法向 = nj
    c2, n = c2p_from_dfield(d2, nj, dx)
    med = float(np.median(c2)) if c2.size else float('nan')
    print()
    print('  ## **C-2 已知答案**（平界面，法向 = `ncmp`）')
    print('     `c2p` 中位 = **%.4f**（%d 胞）%s'
          % (med, n, '✅' if abs(med - 1) < 0.02 else '❌'))

    # ---- C-3′ 理论零基准：球 ----
    print()
    print('  ## **C-3′ 理论零基准**（球 ⇒ 法向在球面上均匀 ⇒ 理论 @@\\mathbb E[\\cos^2]=1/3@@）')
    for Rf in (0.20, 0.32, 0.42):
        ds = synth_sphere(N, dx, i, j, Rf)
        cc, nn = c2p_from_dfield(ds, nj, dx)
        if cc.size:
            print('     R=%.2f·L：均值 = **%.4f**（中位 %.4f，%d 胞）'
                  '  相对 1/3 = %+.2f%%'
                  % (Rf, float(cc.mean()), float(np.median(cc)), nn,
                     100 * (cc.mean() - TH) / TH))
    # 合并（多个半径一起）
    allc = []
    for Rf in (0.18, 0.22, 0.26, 0.30, 0.34, 0.38, 0.42):
        cc, _ = c2p_from_dfield(synth_sphere(N, dx, i, j, Rf), nj, dx)
        if cc.size:
            allc.append(cc)
    allc = np.concatenate(allc) if allc else np.zeros(0)
    if allc.size:
        se = float(allc.std(ddof=1) / np.sqrt(allc.size))
        print('     **合并** %d 胞：均值 = **%.5f ± %.5f(SE)**（理论 0.33333）'
              ' ⇒ 偏差 %+.3f%%'
              % (allc.size, float(allc.mean()), se,
                 100 * (allc.mean() - TH) / TH))

    # ---- C-3″ 平界面对照：逐取向报样本数 + 合并 ----
    print()
    print('  ## **C-3″ 平界面对照**（随机取向；逐取向报样本数，再合并）')
    rng = np.random.default_rng(11)
    meds, pooled = [], []
    for t in range(8):
        u = rng.standard_normal(3)
        u /= np.linalg.norm(u)
        dd = 2.0 * ((X - 0.5 * N * dx) @ u)
        cc, nn = c2p_from_dfield(dd, nj, dx)
        if cc.size:
            meds.append(float(np.median(cc)))
            pooled.append(cc)
    pooled = np.concatenate(pooled) if pooled else np.zeros(0)
    print('     逐取向中位 = %s' % ['%.4f' % m for m in meds])
    if meds:
        print('     逐取向中位的**散布**：min %.4f … max %.4f（**%.1f 倍**）'
              % (min(meds), max(meds), max(meds) / max(min(meds), 1e-12)))
    if pooled.size:
        print('     **合并** %d 胞：均值 = **%.5f**（理论 1/3）⇒ %s'
              % (pooled.size, float(pooled.mean()),
                 '✅ 与理论一致' if abs(pooled.mean() - TH) < 0.02 else '⚠ 偏离理论'))

    # ---- C-4 实测：saSet2 的 F2 胞 ----
    print()
    print('  ## **C-4 实测**：`saSet2` step 400 的 F2 胞（法向 = ∇(φ_k−φ_l)，与 `advance` 同量）')
    d = os.path.join(MB, 'dry_saSet2')
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    z = np.load(fs[-1], allow_pickle=True)
    NN = int(z['N'])
    dxx = 62.5e-9
    mf = os.path.join(d, 'meta.json')
    if os.path.exists(mf):
        dxx = float(json.load(open(mf)).get('dx_nm', 62.5)) * 1e-9
    reg = np.asarray(z['region'], np.int64)
    vk = np.asarray(z['vmap_keys'], np.int64)
    vv = np.asarray(z['vmap_vals'], np.int64)
    var = np.full(int(vk.max()) + 1, -1, np.int64)
    var[vk] = vv
    p = rebuild(z)
    fin = np.isfinite(p)
    karr = np.argmin(np.where(fin, p, np.inf), 0)
    larr = np.argsort(np.where(fin, p, np.inf), 0)[1]
    # F2 胞：karr>0, larr>0, 变体不同（**`§172` 已证投影 10 的臂里确实存在**）
    vka = var[np.clip(karr, 0, var.size - 1)]
    vla = var[np.clip(larr, 0, var.size - 1)]
    mF2 = (karr > 0) & (larr > 0) & (vka > 0) & (vla > 0) & (vka != vla)
    print('     F2 胞（`(karr,larr)` 基）= **%d**' % int(mF2.sum()))
    out, outwide, used = [], [], 0
    pairs = {}
    ii = np.where(mF2)
    for a, b in zip(karr[ii].tolist(), larr[ii].tolist()):
        pairs[(a, b)] = pairs.get((a, b), 0) + 1
    for (a, b) in sorted(pairs, key=lambda t: -pairs[t])[:12]:
        va, vb = int(var[a]), int(var[b])
        lo, hi = min(va, vb), max(va, vb)
        if not np.isfinite(ncmp[hi, lo]).all():
            continue
        njj = ncmp[hi, lo] / np.linalg.norm(ncmp[hi, lo])
        dd = np.asarray(p[a] - p[b], np.float64)
        # ★ 只取**真 a–b 界面胞**：|d| ≤ 1Δx 且该胞 6-邻域里有 region==b 的胞
        near_b = np.zeros(dd.shape, bool)
        for ax in range(3):
            near_b |= (np.roll(reg, 1, ax) == b) | (np.roll(reg, -1, ax) == b)
        m_if = np.isfinite(dd) & (np.abs(dd) <= 1.0 * dxx) & near_b
        cc, nn = c2p_from_dfield(dd, njj, dxx, extra=m_if)
        if cc.size:
            out.append(cc)
            used += nn
        ccw, _ = c2p_from_dfield(dd, njj, dxx)      # 宽口径（作对照，展示差别）
        if ccw.size:
            outwide.append(ccw)
    if not out:
        print('     ⚪ **不适用**（没有可用的 F2 配对/有限 `ncmp`）')
        return 0
    if outwide:
        ow = np.concatenate(outwide)
        print('     **宽口径**（不限定界面胞，**第 38 个自查错误的那个口径**）：'
              '均值 = %.5f（%d 胞）' % (float(ow.mean()), ow.size))
    o = np.concatenate(out)
    se = float(o.std(ddof=1) / np.sqrt(o.size))
    print('     可用 F2 配对 %d 个、胞 %d 个' % (len(out), o.size))
    print('     `c2p` 均值 = **%.5f ± %.5f(SE)**；中位 = %.5f；分位 [10/50/90] = %s'
          % (float(o.mean()), se, float(np.median(o)),
             np.array2string(np.percentile(o, [10, 50, 90]), precision=4)))
    zsc = (o.mean() - TH) / se
    print('     ⇒ 与理论零基准 1/3 比：**z = %+.2f** %s'
          % (zsc, '⇒ ✅ **显著偏向不变平面（`ncmp` 生效）**' if zsc > 3 else
             ('⇒ ⚠ 显著**偏离**不变平面' if zsc < -3 else
              '⇒ ❌ **与随机取向无显著差别**')))
    print()
    print('  ⚠ 记账：C-3′ 用**球**（取向覆盖均匀、胞数上万）⇒ 零基准有**理论值 1/3**，')
    print('     不再依赖"测一个基线"；C-3″ 展示原来 7 倍散布的来源是**逐取向小样本**。')
    print('     ⚠ 实测的法向估计量与 `advance` 同源（`∇(φ_k−φ_l)`），但**不是**同一段代码。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
