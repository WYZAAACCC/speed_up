#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r78_pairselfac.py —— **块间自协调的"零模型"表**（纯离线，不跑仿真）。

## 为什么

`BLOCK_SELFAC.md` §3 给了群级自协调判据
    @@r(G) = || Σ_{i∈G} f_i·dev(ε⁰_i) || / scale@@，  `scale` = 12 个变体 `||dev ε⁰||` 的均值
并断言：**最小自协调规模 `k* = 6`**，且 64 个自协调六元组 = "6 个 {110}β 惯习面各取一个"。
§7.1 **P-SA-1** 把「`var_rule='ed'` 臂的 `r_obs` 显著低于 `'random'` 对照臂」定为判据。
`BLOCK_SELFAC.md:531` 还**明确推荐**用 **V1&V2**（`n*` 近反平行、经典自协调对）而不是 V1&V3。

**但 R75 用的是 `--laths 1,1,1,3,3,3`（V1&V3）。** 本脚本回答：
  * 这个选择让自协调判据**变得没有分辨力了吗**？（若 `r(V1,V3)` 与"随机配对"同量级 ⇒ 是）
  * 哪个对/三元组才是这套 `EPS0` 下真正自协调的？
  * `BLOCK_SELFAC.md` §3 的 `k*=6` 断言，在这份 `EPS0` 上**复核**是否成立？

## 口径（**必须先说清楚，否则比值无意义**）

* `E_i ≡ dev(ε⁰_i) = ε⁰_i − tr(ε⁰_i)/3·I`（与 `_bk_measure.blocks()` 的 `r_selfac` **同一口径**）
* `scale ≡ mean_i ||E_i||_F`（同上）
* `r_selfac(G) ≡ ||Σ_{i∈G} f_i E_i||_F / scale`（`f_i` = 体积分数，`Σf_i = 1`）
* **对残差** `r_pair(v,w) ≡ ||E_v + E_w|| / (||E_v|| + ||E_w||)`
    `= 0` ⇒ 完全抵消（理想自协调对）；`= 1` ⇒ 完全不抵消

⚠ 三个量纲不同的比值**不得混着报**。本脚本每张表都写清用的是哪一个。
"""
from __future__ import annotations

import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from T16_verify_rve import EPS0, NPF                          # noqa: E402

TOL = 1e-9


def dev(A):
    A = np.asarray(A, float)
    return A - np.trace(A) / 3.0 * np.eye(3)


def _npf(v):
    """`NPF` 兼容 1 基 dict / list（实测它是按**变体号 1..12** 索引的）。"""
    try:
        return np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        return np.asarray(NPF[v - 1], float)


def _simplex_r(mats, scale):
    """`min_{f∈Δ} ||Σ f_i E_i||_F / scale` —— **单纯形上的最小范数点**。

    做法：先用 `nnls` 解"把 0 表示为非负组合"的最小二乘，再归一化。
    若 `E` 张成的凸包含 0，`nnls(0 目标)` 会给出范数 ~0 的解。
    为稳妥另加**投影梯度**兜底：在单纯形上直接做条件梯度（Frank–Wolfe），
    两者取小 —— 这一步是**量具**，不能靠单一求解器（教训 #19）。
    """
    from scipy.optimize import nnls
    A = np.asarray(mats, float)                 # (k, 9)
    k = A.shape[0]
    # ---- 法一：凸包原点判定（LP 型）⇒ 最小二乘非负解 ----
    b = np.ones(k) / k
    try:
        f1, _ = nnls(A.T, np.zeros(9))
        n1 = float(np.linalg.norm(A.T @ f1))
        s1 = float(f1.sum())
        r1 = (n1 / s1) if s1 > 1e-12 else float('inf')
    except Exception:                                       # pragma: no cover
        r1 = float('inf')
    # ---- 法二：Frank–Wolfe（条件梯度）在单纯形上最小化 ||Σ f E||² ----
    f = b.copy()
    for _ in range(600):
        # ∇_f ||Aᵀ f||² = 2 A (Aᵀ f)，形状 (k,)；线性子问题的最优顶点 = argmin ∇
        g = A @ (A.T @ f)
        j = int(np.argmin(g))
        d = np.zeros(k)
        d[j] = 1.0
        d -= f
        # 精确线搜索（二次函数）：min_γ ||Aᵀ(f+γd)||²，γ ∈ [0,1]
        Ad = A.T @ d
        Af = A.T @ f
        den = float(Ad @ Ad)
        if den < 1e-300:
            break
        gamma = -float(Af @ Ad) / den
        gamma = min(1.0, max(0.0, gamma))
        f = f + gamma * d
        if gamma < 1e-14:
            break
    r2 = float(np.linalg.norm(A.T @ f)) / scale
    r1 = r1 / scale
    return min(r1, r2)


def main():
    E = [dev(e) for e in EPS0]
    nrm = [float(np.linalg.norm(e)) for e in E]
    scale = float(np.mean(nrm))
    print('=' * 104)
    print('_r78_pairselfac —— 块间自协调的零模型表（口径见文件头）')
    print('=' * 104)
    print('  scale = mean||E_i|| = %.6e   （12 个变体）' % scale)
    print('  单变体 r_selfac = ||E_v||/scale:  '
          + '  '.join('V%d:%.3f' % (v + 1, nrm[v] / scale) for v in range(12)))
    print('  Σ_v E_v = %.3e （应 ≈ 0：12 个变体整体自协调）'
          % float(np.linalg.norm(np.sum(E, axis=0))))
    print()

    # ---------- 表 1：对残差 r_pair（**与体积分数无关**） ----------
    print('=' * 104)
    print('表 1 对残差 `r_pair(v,w) = ||E_v+E_w||/(||E_v||+||E_w||)`'
          '   [0=完全抵消, 1=完全不抵消]')
    print('=' * 104)
    print('      ' + ''.join('%-8s' % ('V%d' % (w + 1)) for w in range(12)))
    pairs = []
    for v in range(12):
        row = []
        for w in range(12):
            if v == w:
                row.append('   —    ')
                continue
            r = float(np.linalg.norm(E[v] + E[w])) / (nrm[v] + nrm[w])
            row.append('%7.3f ' % r)
            if v < w:
                pairs.append((r, v + 1, w + 1))
        print('  V%-3d' % (v + 1) + ''.join(row))
    pairs.sort()
    print()
    print('  **最自协调的 8 对**（r_pair 最小）：')
    for r, v, w in pairs[:8]:
        nv = np.asarray(NPF[v], float); nw = np.asarray(NPF[w], float)
        nv = nv / np.linalg.norm(nv); nw = nw / np.linalg.norm(nw)
        ang = np.degrees(np.arccos(np.clip(abs(float(nv @ nw)), -1, 1)))
        print('     V%-2d & V%-2d   r_pair = %.4f   |∠(n*,n*)| = %6.2f°'
              % (v, w, r, ang))
    print()
    print('  **最不自协调的 4 对**（r_pair 最大）：')
    for r, v, w in pairs[-4:]:
        print('     V%-2d & V%-2d   r_pair = %.4f' % (v, w, r))
    print()

    # ---------- 表 2：文献点名的候选对 ----------
    print('=' * 104)
    print('表 2 **文献/框架文档点名的候选对**，以及 R75 实际用的那一对')
    print('=' * 104)
    def show(v, w, note):
        r = float(np.linalg.norm(E[v - 1] + E[w - 1])) / (nrm[v - 1] + nrm[w - 1])
        nv = np.asarray(NPF[v], float); nv /= np.linalg.norm(nv)
        nw = np.asarray(NPF[w], float); nw /= np.linalg.norm(nw)
        ang = np.degrees(np.arccos(np.clip(abs(float(nv @ nw)), -1, 1)))
        # 50/50 混合的群级残差（**与 `blocks()` 的 `r_selfac` 同口径**）
        mix = 0.5 * (E[v - 1] + E[w - 1])
        rg = float(np.linalg.norm(mix)) / scale
        print('  V%-2d & V%-2d  r_pair=%.4f  |∠(n*,n*)|=%6.2f°  '
              '50/50 群级 r_selfac=%.4f   %s'
              % (v, w, r, ang, rg, note))
        return r, rg
    r12 = show(1, 2, '← `BLOCK_SELFAC.md:531` 推荐的**经典自协调对**（n* 反平行）')
    r13 = show(1, 3, '← **R75 实际用的那一对**（`--laths 1,1,1,3,3,3`）')
    show(1, 1, '（同变体 ⇒ 定义上不抵消，F3 低角晶界）')
    print()
    print('  ⇒ **R75 的对照有没有分辨力？**  r_pair(V1,V3) = %.4f  vs  r_pair(V1,V2) = %.4f'
          % (r13[0], r12[0]))
    if r13[0] > 0.5 and r12[0] < 0.5:
        print('     → **有**：V1&V3 几乎不抵消，V1&V2 明显抵消 ⇒ 选 V1&V3 去测自协调'
              '等于**在一个判据几乎不动的位置上做实验**')
    else:
        print('     → 两者同量级 ⇒ 需另找判据量')
    print()

    # ---------- 表 3：k=1..6 的**单纯形最优**（复核 §3 的 k*=6 断言） ----------
    print('=' * 104)
    print('表 3 `min_G min_{f∈Δ} r_selfac`（**对单纯形取最小**，与 §3.1 定义逐字一致）')
    print('=' * 104)
    print('  %-4s %-14s %-30s %-10s %s'
          % ('k', 'r_min', '最优组合（1 基）', 'r<1e-6 数',
             'max_G r_min(G) ★'))
    VEC = np.array([e.reshape(-1) for e in E])              # (12, 9)
    for k in range(1, 7):
        best = None
        # ⚠ 这一列**不是**文档 §3.2 的 `r_max`（那是"对 f 取最大"，本脚本没算）。
        #   它是"**最差的子集**其单纯形最小残差" —— 名字必须写清，否则又是一次
        #   "跨量比值"误读（本仓库硬规程②）。
        worst = -1.0
        nzero = 0
        for G in itertools.combinations(range(12), k):
            if k == 1:
                r = nrm[G[0]] / scale
            else:
                r = _simplex_r(VEC[list(G)], scale)
            if r < 1e-6:
                nzero += 1
            worst = max(worst, r)
            if best is None or r < best[0]:
                best = (r, G)
        print('  %-4d %-14.6g %-30s %-10d %.4f'
              % (k, best[0], str(tuple(i + 1 for i in best[1])), nzero, worst))
    print()
    print('  对照 `BLOCK_SELFAC.md §3.2` 的表：')
    print('     k=2: r_min 0.522 / r_max 0.996 / r<tol 0')
    print('     k=3: 0.174 / 1.000 / 0')
    print('     k=4: 0.150 / 0.898 / 0')
    print('     k=5: 0.0945 / 0.573 / 0')
    print('     k=6: 4.3e-15 / 0.573 / **64**')
    print()
    # ---------- 惯习面分组 + 变体对是否同面 ----------
    print('=' * 104)
    print('表 4 **惯习面分组**（`|cos|` 判同，阈值 1e-6；与 `blocks()` 的 `n_habit` 同口径）')
    print('=' * 104)
    nrml, grp = [], {}
    for v in range(1, 13):
        nv = np.asarray(_npf(v), float)
        nv = nv / np.linalg.norm(nv)
        hit = None
        for gi, u in enumerate(nrml):
            if abs(abs(float(nv @ u)) - 1.0) < 1e-6:
                hit = gi
                break
        if hit is None:
            nrml.append(nv)
            hit = len(nrml) - 1
        grp.setdefault(hit, []).append(v)
    print('  共 %d 个不同的惯习面族：%s'
          % (len(nrml), '   '.join(str(sorted(g)) for g in grp.values())))
    for v, w in ((1, 2), (1, 3), (1, 5), (1, 11)):
        nv = np.asarray(_npf(v), float); nv /= np.linalg.norm(nv)
        nw = np.asarray(_npf(w), float); nw /= np.linalg.norm(nw)
        dot = float(nv @ nw)
        same = any(v in g and w in g for g in grp.values())
        print('   V%-2d & V%-2d : n*·n* = %+.4f  ⇒ %s'
              % (v, w, dot, '**同一个惯习面**（族内 2 个变体）' if same
                 else '不同惯习面'))
    print()
    print('  ⇒ `BLOCK_SELFAC.md:531` 写 "V1&V2 … `n*` 反平行，`n*·n* = −0.996`，'
          '各自的自协调剪切互相抵消"。')
    print('     **本表实测**：V1&V2 的 `n*·n*` = %+.4f（**近平行**，同一个惯习面），'
          % float(np.asarray(_npf(1), float) @ np.asarray(_npf(2), float)
                  / (np.linalg.norm(_npf(1)) * np.linalg.norm(_npf(2)))))
    print('     而 `r_pair` = %.4f —— 与**同一文档 §3.4** 的"同惯习面 ⇒ 0.996"一致，'
          % r12[0])
    print('     与 §7 的"自协调对"**矛盾**。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
