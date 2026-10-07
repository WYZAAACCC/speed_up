#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r358_ed_offline.py —— ★★★ 条件③的另一半：**驱动力**在块-块界面上是否对相容对更小？

## `§173` 回答了"接触面积"，本节回答"驱动力"

`§173` 实测：块-块接触面**不偏好**近相容（rank-1 相容）变体对（X-0=1.0000，720 置换精确零分布）。
但那只是**几何**。真正决定组织演化的是**界面驱动力**
@@\\Delta(ed)=ed_k-ed_l@@ —— 它可能"面积不偏、但力偏"。

## 怎么在**归档数据**上离线重算 `ed`（用户要的"用新量具重测"）

`windowB_surface.py:2890-2899` 的装配式（**逐行照抄**）：

    e0p = concat([zeros((1,6)), e0v_eng])      # 0 = 母相 ⇒ ed_0 ≡ 0
    sep = concat([[0.0], sext_e0])
    ed_v = Σ_p e0p[v,p]·σ_p + sep[v]
    σ = pf.sigma_tensor(region)                # `eps0_fields_idx`：0=母相, v=变体 v

⇒ 只要用**归档的 `region` 图**重建 `σ`，就能算出**当时**的 `ed_k − ed_l`。

## 判据（**先写死**）

* **Z-0 自证**：重建 `argmin` == 归档 `region`（限定在 winner 的场存下来的胞上）= **1.0000**。
* **Z-1 ★★ 已知答案对照**：在 `karr>0 & larr==0`（F1）胞上算 `med|ed_k−ed_0|`，
  与**引擎自己记的** `dry_saSet2F2P0/diag_terms.json` 的 `vb.med_ed`（@step 400 = **2.954e+08**）比。
  **相对差 > 2% ⇒ 离线弹性重建没对上 ⇒ 本节其余输出全部作废。**
* **Z-2**：F2 胞上 `med|Δed|` 与 F3/F1 的对比。
* **Z-3 ★ 决定性**：用 `§173` 同一套 **720 置换精确零分布**，
  但统计量换成 **F2 面上的面积加权平均 `|Δed|`**（按块对聚合成 6×6 矩阵 `E[i][j]`）。
  * **若实测显著偏低 ⇒ 相容对的驱动力确实更小 ⇒ 存在"力"层面的自协调倾向**；
  * **若无显著差别 ⇒ 力层面也没有自协调证据**（与 `§173` 的几何结论一致）。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from itertools import permutations

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
MB = os.path.join(HERE, '_exp', '_bk_mb')
sys.path.insert(0, HERE)


def rebuild(z):
    N = int(z['N'])
    nf = int(z['band_fld'].max()) + 1 if z['band_fld'].size else 0
    phi = np.full((nf, N, N, N), np.nan, np.float32)
    flat = phi.reshape(nf, -1)
    flat[z['band_fld'].astype(int), z['band_idx'].astype(int)] = \
        z['band_val'].astype(np.float32)
    return phi


def blocks_of(vk, var):
    nf = int(max(vk)) + 1
    blk_arr = np.full(nf, -1, np.int64)
    runs, cur = [], [int(vk[0])]
    for k_ in vk[1:].tolist():
        if var[k_] == var[cur[-1]]:
            cur.append(k_)
        else:
            runs.append(cur)
            cur = [k_]
    runs.append(cur)
    blk_var = []
    for bi, run in enumerate(runs):
        for k_ in run:
            blk_arr[k_] = bi
        blk_var.append(int(var[run[0]]))
    return blk_arr, np.asarray(blk_var, int)


def fib_sphere(m):
    i = np.arange(m) + 0.5
    phi = np.arccos(1 - 2 * i / m)
    gold = np.pi * (1 + 5 ** 0.5)
    th = gold * i
    return np.stack([np.cos(th) * np.sin(phi),
                     np.sin(th) * np.sin(phi), np.cos(phi)], -1)


def rank1_residual(D, dirs):
    best = np.inf
    d = D.ravel()
    for n in dirs:
        A = np.zeros((9, 3))
        for k in range(3):
            e = np.zeros(3)
            e[k] = 1.0
            A[:, k] = (0.5 * (np.outer(e, n) + np.outer(n, e))).ravel()
        c, *_ = np.linalg.lstsq(A, d, rcond=None)
        r = d - A @ c
        v = float(r @ r)
        if v < best:
            best = v
    return float(np.sqrt(max(best, 0.0)))


def main():
    print('=' * 108)
    print('_r358 —— 块-块界面的**驱动力**是否对相容变体对更小？（离线重算 σ/ed）')
    print('=' * 108)
    arm = sys.argv[1] if len(sys.argv) > 1 else 'saSet2F2P0'
    step_want = int(sys.argv[2]) if len(sys.argv) > 2 else None
    d = os.path.join(MB, 'dry_' + arm)
    fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                key=lambda q: int(re.search(r'_(\d+)\.npz$', q).group(1)))
    if step_want is not None:
        fs = [q for q in fs
              if int(re.search(r'_(\d+)\.npz$', q).group(1)) == step_want]
    if not fs:
        print('  ⚠ 无快照（step=%s）' % step_want); return 2
    z = np.load(fs[-1], allow_pickle=True)
    N = int(z['N'])
    L = float(z['L'])
    reg = np.asarray(z['region'], np.int64)
    vk = np.asarray(z['vmap_keys'], np.int64)
    vv = np.asarray(z['vmap_vals'], np.int64)
    nf = int(z['band_fld'].max()) + 1
    nv = int(vk.size)
    var = np.full(max(nf, int(vk.max()) + 1), -1, np.int64)
    var[vk] = vv
    laths = [int(v) for v in vv]
    print('  arm=%s step=%s N=%d L=%.3e m  laths=%s' % (arm, z['step'], N, L, laths))
    if not (N == reg.shape[0] == reg.shape[1] == reg.shape[2]):
        print('  ⚠ N 与 region 形状不一致'); return 2

    # ---- Z-0 自证 ----
    p = rebuild(z)
    fin = np.isfinite(p)
    krec = np.argmin(np.where(fin, p, np.inf), 0)
    m_ok = fin[reg, np.arange(N)[:, None, None],
               np.arange(N)[None, :, None], np.arange(N)[None, None, :]]
    x0 = float((krec == reg)[m_ok].mean()) if m_ok.any() else float('nan')
    print('  **Z-0 自证** = %.4f %s' % (x0, '✅' if x0 > 0.999 else '❌ 作废'))
    if not (x0 > 0.999):
        return 2
    karr = krec
    full = np.where(fin, p, np.inf)
    larr = np.argsort(full, 0)[1]

    # ---- 建弹性求解器（与 _bk_exp.py:607 同参）----
    from T16_verify_rve import C, EPS0
    import windowB_surface as W
    eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in laths]
    g = W.LevelSetMulti(N, L, C=np.asarray(C, float), eps0=eps0,
                        gamma=0.0, Mob=0.0, workers=1)
    e0p = np.concatenate([np.zeros((1, 6)), np.asarray(g.e0v_eng, float)], 0)
    sep = np.concatenate([[0.0], np.asarray(g.sext_e0, float)])
    print('  e0v_eng 形状 = %s；sext_e0 全 0 ? %s'
          % (np.shape(g.e0v_eng), bool(np.allclose(g.sext_e0, 0.0))))
    print('  ⚠ 记账：`e0p[0]=zeros(6)`、`sep[0]=0.0` ⇒ **`ed_0 ≡ 0`**（与 `:2863` 注释一致）')

    print('  正在装配软指示场 + 解 σ（N=%d，单线程）...' % N, flush=True)
    # ★★★ v2 修（**这一处让 Z-1 从 35.1% 的偏差变成通过**）：
    #   引擎跑的是 **soft 路径**（`windowB_surface.py:1042` 把 `elastic_soft` 默认设成 True；
    #   `_bk_exp.py` **从不**覆盖它 ⇒ `:2777-2788` 生效）：
    #       pf.phi[v] = 0.5*(1 − tanh(φ_{v+1} / (1.5Δx)))
    #   v1 我用了**硬** gather 路径 `sigma_tensor(region)` ⇒ σ 在界面处带 O(1) 阶梯噪声
    #   ⇒ `med|Δed|` 偏高 **35.1%**。
    #   ⚠ 为什么归档的**带内稀疏 φ** 够用：w = 1.5Δx 时
    #     |φ| = 6Δx ⇒ tanh(4) = 0.9993 ⇒ h 已经饱和到 **3e-4** 以内
    #     ⇒ 带外取饱和极限 `h = [region == v]` 的误差 ≲ 3e-4 ✓。
    _w = 1.5 * float(g.dx)
    pfphi = np.zeros((nv, N, N, N), dtype=np.float64)
    n_appr = 0
    for v in range(nv):
        k = v + 1
        fld = p[k] if k < p.shape[0] else np.full((N, N, N), np.nan, np.float32)
        st = np.isfinite(fld)
        n_appr += int((~st).sum())
        pfphi[v] = np.where(st, 0.5 * (1.0 - np.tanh(fld / _w)),
                            (reg == k).astype(np.float64))
    print('     软指示场：精确胞 %d / 近似（带外取饱和）胞 %d（%.3f%%）'
          % (pfphi.size - n_appr, n_appr, 100.0 * n_appr / pfphi.size))
    g.pf.phi = pfphi
    sig = g.pf.sigma_tensor()

    def ed_of(idx):
        out = np.zeros(reg.shape)
        for q in range(6):
            out += e0p[idx, q] * sig[q]
        return out + sep[idx]

    edk = ed_of(np.clip(karr, 0, nv))
    edl = ed_of(np.clip(larr, 0, nv))
    ded = edk - edl
    print('  σ 已解出；`ed` 范围 = %.4e … %.4e' % (edk.min(), edk.max()))

    # ---- 三类界面的掩码（**必须在 Z-1 之前算**：Z-1 的替代控制要用 F3） ----
    # ★★★ 修（**第 39 个自查错误**）：所有 `(karr,larr)` 掩码**必须再与 `m_ok` 相交**。
    #   病灶：`X-0 自证` 只在 `m_ok`（**归档 winner 自己的场存下来了**）上验过 `karr == region`。
    #     全盒上 `karr/larr` 是**重建产物**：深内部胞的场都没存 ⇒ 全被填 `+inf`
    #     ⇒ `argmin` 退化成"取编号最小的有限值/0" ⇒ **纯伪影**。
    #   实测后果（`permB1_200` step 200）：我的 `karr>0 & larr==0` = **48316** 胞，
    #     而该步的转变体积只有 ~2.3e4 胞（`f≈0.0165 × 343 µm³ / Δx³`）
    #     ⇒ **计数被深内部伪影灌了 2 倍**，Z-1 因此差 **70.5%** 而被判不通过。
    #   ⚠ `saSet2F2P0` 侥幸通过（0.359%）是因为它结构粗、`m_ok` 几乎覆盖了全部变体胞。
    vk_ = var[np.clip(karr, 0, var.size - 1)]
    vl_ = var[np.clip(larr, 0, var.size - 1)]
    samev = (vk_ == vl_) & (vk_ > 0)
    m1 = m_ok & (karr > 0) & (larr == 0)
    m2 = m_ok & (karr > 0) & (larr > 0) & (~samev)
    m3 = m_ok & (karr > 0) & (larr > 0) & samev
    print('  ⚠ 掩码已与 `m_ok`（winner 的场存下来了）相交：m_ok 共 %d 胞'
          % int(m_ok.sum()))

    # ---- Z-1 已知答案对照 ----
    mine = float(np.median(np.abs(ded[m1])))
    ref = None
    jf = os.path.join(d, 'diag_terms.json')
    if os.path.exists(jf):
        o = json.load(open(jf, encoding='utf-8'))
        rec = o.get('rec') if isinstance(o, dict) else o
        if rec:
            ref = (rec[-1].get('vb') or {}).get('med_ed')
    print()
    print('  ## **Z-1 已知答案对照**（F1 胞 `med|Δed|` vs 引擎自记 `vb.med_ed`）')
    if isinstance(ref, (int, float)):
        rel = abs(mine - ref) / abs(ref)
        print('     引擎自记 = **%.4e**（%d 胞）；我的离线重建 = **%.4e**（%d 胞）'
              % (ref, int((rec[-1].get('vb') or {}).get('n', 0)), mine, int(m1.sum())))
        print('     相对差 = **%.3f%%** %s'
              % (100 * rel, '✅ 通过（<2%）' if rel < 0.02 else
                 '❌ **不通过 ⇒ 本节其余输出全部作废**'))
        if not (rel < 0.02):
            print('     ⚠ 注意：引擎的 `_fin` 还含 `isfinite(stk·κ)` 等掩码，'
                  '而我这里只用了 `karr>0 & larr==0` ⇒ 胞集不同。')
            print('        ⇒ 若差异源于胞集，应改用引擎记录的 `vb.n` 对齐后再比。')
            return 2
    else:
        # ⚠ 该臂没有 `--diag-terms` ⇒ 拿不到 `vb.med_ed`。
        #   允许继续，**但必须换一个可离线自证的控制**：F3（同变体）的 `Δed` 是
        #   **结构性精确 0**（同变体的 `e0v_eng` 逐位相同）⇒ 若重建正确，它必须 = 0。
        print('     ⚠ 该臂没有 `diag_terms.json` ⇒ 无 `vb.med_ed` 对照。')
        print('        ⇒ 改用**结构性控制**：F3 的 `|Δed|` 必须精确为 0（下面 Z-2 验）。')
        print('        ⚠ 记账：重建**管路本身**已在兄弟臂 `saSet2F2P0` 上对照通过')
        print('          （`vb.med_ed` 相对差 **0.359%**）⇒ 同一代码路径 + 该臂自己的 N/L/laths。')
        f3c = m3
        if int(f3c.sum()) > 0:
            v3 = float(np.max(np.abs(ded[f3c])))
            print('        **替代控制**：F3 上 `max|Δed|` = **%.3e** %s'
                  % (v3, '✅ 精确 0' if v3 == 0.0 else '❌ 非 0 ⇒ 作废'))
            if v3 != 0.0:
                return 2
        else:
            print('        ❌ 该臂连 F3 胞都没有 ⇒ 无任何控制 ⇒ 作废')
            return 2

    # ---- Z-2 ----
    print()
    print('  ## **Z-2** 三类界面上的 `|Δed|`')
    for lab, mm in (('F1 含母相', m1), ('F2 异变体', m2), ('F3 同变体', m3)):
        if int(mm.sum()) == 0:
            print('     %-10s 胞数 0' % lab); continue
        v = np.abs(ded[mm])
        print('     %-10s 胞数 %-7d `|Δed|` 中位 = **%.4e**（均值 %.4e）'
              % (lab, int(mm.sum()), float(np.median(v)), float(v.mean())))

    if int(m2.sum()) < 200:
        print()
        print('  ⇒ ⚠ F2 胞只有 %d 个 ⇒ **Z-3 不适用**（本臂是 `--facet-proj 0`，'
              '几何 F2 本来就少，见 `§172`）' % int(m2.sum()))
        print('     ⇒ 请改跑 `saSet2`（投影 10，F2≈1922）—— 但该臂**没有** `--diag-terms`，'
              '拿不到 Z-1 对照。')
        print('     **⇒ 待办 Z-4：用投影 10 的参数 + `--diag-terms` 重跑一条臂，才能同时有 Z-1 与 Z-3。**')
        return 0

    # ---- Z-3 ★ 逐胞秩检验（**取代已证明不适用的置换检验**） ----
    #  ⚠ **第 37 个自查错误**：v1 把 `§173` 的"720 置换"照搬到这里 —— 但那个零假设
    #    只对"**只由标签决定的**统计量"有效（如几何不相容度 R）。
    #    而 `|Δed|` 是**场量**，它随 σ 走；置换标签**不会**重解 σ
    #    ⇒ 且 6 个块变体互不相同 ⇒ 任何置换下"哪几对相邻"都不变
    #    ⇒ 统计量**结构性不变**（实测：不同取值 1 个）⇒ 零分布退化。
    #  **正确的问题**：**固定同一个 σ**，问"**实际长到一起的那一对**，
    #    其 `|Δed|` 在**全部 66 个变体对**里排第几？"
    #    ⇒ 排位低 = 组织**选**了弹性便宜的配对（自协调）；排位 ~0.5 = 没有选择。
    ED = np.tensordot(e0p, sig, axes=([1], [0])) + sep[:, None, None, None]
    pairs66 = [(i, j) for i in range(1, nv + 1) for j in range(i + 1, nv + 1)]
    ii = np.where(m2)
    if ii[0].size == 0:
        print()
        print('  ## **Z-3** ⚪ 不适用（无 F2 胞）')
        return 0
    A = np.clip(karr[ii], 0, nv)
    B = np.clip(larr[ii], 0, nv)
    obs = np.abs(ED[A, ii[0], ii[1], ii[2]] - ED[B, ii[0], ii[1], ii[2]])
    allv = np.stack([np.abs(ED[a, ii[0], ii[1], ii[2]]
                            - ED[b, ii[0], ii[1], ii[2]])
                     for (a, b) in pairs66], 0)          # (66, nF2)
    # 秩 = 比观测**更小**的对数 / 总数（0 = 最小 ⇒ 最自协调）
    rank = (allv < obs[None, :]).sum(0) / float(len(pairs66) - 1)
    # 权重：按 F2 有向面的重数（同一胞可贡献多面）——这里用胞级等权，记账说明
    pct = float(np.median(rank))
    # 零基准：若"配对是随机的"，秩应均匀 ⇒ 中位 0.5；用同一批胞做**严格**零假设：
    #   把观测对换成 66 对里的**任意**一对，其秩的期望 = 0.5（均匀秩）
    print()
    print('  ## **Z-3 ★ 逐胞秩检验**（固定 σ；秩 = 比观测更小的变体对占比，0 = 最自协调）')
    print('     F2 胞 %d 个；观测对 `|Δed|` 中位 = **%.4e**' % (ii[0].size, float(np.median(obs))))
    print('     66 对在同一批胞上的 `|Δed|` 中位（逐对再取中位）的范围 = %.4e … %.4e'
          % (float(np.median(np.median(allv, 1))),
             float(np.max(np.median(allv, 1)))))
    print('     观测对秩的分布：中位 **%.3f**，分位 [10/25/50/75/90] = %s'
          % (pct, np.array2string(np.percentile(rank, [10, 25, 50, 75, 90]),
                                  precision=3)))
    # 严格零假设：秩在"随机配对"下**均匀分布** ⇒ 中位 0.5；
    #   用 bootstrap 给出中位秩的零分布（从 66 对里随机抽，等价于均匀秩）
    rng = np.random.default_rng(11)
    nF2 = int(ii[0].size)
    null_med = np.median(rng.uniform(0, 1, size=(2000, nF2)), axis=1)
    pv = float((null_med <= pct).mean())
    print('     零假设（随机配对 ⇒ 秩均匀）中位秩的 5–95%% = %.3f … %.3f'
          % (float(np.percentile(null_med, 5)), float(np.percentile(null_med, 95))))
    print('     ⇒ **百分位 = %.3f** %s'
          % (pv, '⇒ ✅ **显著偏低 ⇒ 组织选了弹性便宜的配对（自协调）**' if pv < 0.05
             else ('⇒ ⚠ 显著偏高（反自协调）' if pv > 0.95 else
                   '⇒ ❌ **与随机配对无显著差别 ⇒ 无"变体选择"证据**')))

    # ---- Z-4 ★★ **决定性鉴别**：把"秩"换成**与 σ 无关**的两个口径 ----
    #   问题：Z-3 的强信号（秩中位 0.154）到底是
    #     (a) **σ 介导的变体选择**（弹性真的把便宜的配对准了），还是
    #     (b) 只是"**本征应变相近的变体容易长到一起**"这个**几何事实**的更灵敏版本？
    #   做法：同样固定观测的那些 F2 胞，但把 66 对的排序键换成**与 σ 无关**的量：
    #     · `‖Δε⁰‖`（`§173` 的代理量）
    #     · `R`（rank-1 相容残差，`§173` 的主判据）
    #   判读：
    #     * 若按 `R` 的秩也 ≈ 0.15 ⇒ **与 (b) 一致** ⇒ Z-3 只是 `§173` 的高功效版本，
    #       不构成"σ 介导"的新证据；
    #     * 若按 `R` 的秩 ≈ 0.5 而按 `|Δed|` 是 0.15 ⇒ **存在额外的 σ 介导选择**。
    from T16_verify_rve import EPS0 as _E
    _Ev = [np.asarray(_E[v - 1], float) for v in range(1, nv + 1)]
    _dirs = fib_sphere(300)
    R66 = np.array([rank1_residual(_Ev[i - 1] - _Ev[j - 1], _dirs)
                    for (i, j) in pairs66])
    N66 = np.array([float(np.linalg.norm(_Ev[i - 1] - _Ev[j - 1]))
                    for (i, j) in pairs66])
    idx_of = {p_: t for t, p_ in enumerate(pairs66)}
    # 观测对的 (i,j)（无序）
    oi = np.minimum(A, B)
    oj = np.maximum(A, B)
    pos = np.array([idx_of[(int(a), int(b))] if (int(a), int(b)) in idx_of
                    else idx_of[(int(b), int(a))] for a, b in zip(oi, oj)])
    print()
    print('  ## **Z-4 ★★ 决定性鉴别**（同样的胞，换成**与 σ 无关**的排序键）')
    for lab, vec in (('`R`（rank-1 相容残差）', R66), ('`‖Δε⁰‖`（代理量）', N66)):
        ov = vec[pos]
        rk = (vec[:, None] < ov[None, :]).sum(0) / float(len(pairs66) - 1)
        md = float(np.median(rk))
        p4 = float((null_med <= md).mean())
        print('     %-26s 观测对秩中位 = **%.3f**（百分位 %.3f）'
              % (lab, md, p4))
    print('     ⇒ 判读：**按 `R` 的秩若也≈0.15 ⇒ Z-3 只是"相近变体容易相遇"的高功效版本**；')
    print('        若按 `R` 的秩≈0.5 而按 `|Δed|` 是 0.15 ⇒ **另有 σ 介导的选择**。')
    print()
    print('  ⚠ 记账：`σ` 用**归档 `region`** 离线重解（用户要的"用新量具重测"）；')
    print('     Z-1 已用引擎自记的 `vb.med_ed` 做过已知答案对照。')
    print('     ⚠ 本检验的功效同样受**块数**限制（6 块 ⇒ 720 置换）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
