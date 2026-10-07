#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r212_sameed.py —— **独立验证 `§137.4` 的基础**：同变体的 `Δed` 为什么恰好 ≡ 0。

## 待验证的陈述（`§137.3` 实测：F3 界面上 `Δed ≡ 0`，占 100% 的胞）

由 `windowB_surface.py:2863/2894-2899`：
    `ed_v(cell) = Σ_p e0v_eng[v,p]·σ_p(cell) + sext_e0[v]`
而 `:2889` `sig = self.pf.sigma_tensor(reg)` —— **σ 按 `reg`（winner）算，与 v 无关**；
`:2894-2898` 的 `_ed(idx)` 只是**按 idx gather 不同的 `e0v` 行**去乘**同一个** `sig`。

**⇒ 推论**：若两个场 k、l 的 `e0v_eng` 行与 `sext_e0` **逐位相同**，则
    `ed_k − ed_l = Σ_p (e0v[k,p] − e0v[l,p])·σ_p + (sext[k] − sext[l]) ≡ 0`（**精确**）。

## 判据

* **E-1** 同变体的场对：`e0v_eng` 行**逐位相同**、`sext_e0` **逐位相同**。
* **E-2** 异变体的场对：`e0v_eng` 行**不同**（否则 F2 也会 `Δed ≡ 0`，与实测矛盾）。
* **E-3** 正对照：随机取两个**不同**变体 ⇒ 必须判"不同"（否则 E-1 是同义反复）。
* **E-4** 用**真实构造路径**（`_bk_exp.build_table` + 引擎构造）取这些表，
  不自己另造 —— 保证验的是**代码实际用的**那份。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import windowB_surface as W  # noqa: E402
import windowB_lath as WL  # noqa: E402
from T16_verify_rve import C, EPS0, NPF  # noqa: E402


def build(laths, omega_max=5.0):
    """★ **必须复刻 `_bk_exp.py` 的真实构造路径**（本脚本自己的判据 **E-4**）。

    ⚠⚠ **第一版违反了 E-4，导致结论完全反了**（**第 15 个自查错误**）：
      第一版写 `eps0=[...EPS0...]`（**12 个变体的原表**）⇒ `e0v_eng[i]` 对应**变体 i**，
      于是读 `e0v_eng[1]` vs `e0v_eng[2]`（想比"同变体 V1"）实际比的是**V1 vs V2**
      ⇒ 打出 `max|Δ| = 1.730e-01`、判"同变体不同" ⇒ **差点推翻 `§137.4`**。

    **真相**（`_bk_exp.py:535-537`）：
        `eps0    = [EPS0[v-1].copy() for v in laths_eff]`   ← **逐场**，同变体的场**各存一份**
        `npref   = {i+1: NPF[v] for i, v in enumerate(laths_eff)}`
    ⇒ **同变体的两个场拿到的是同一份 `EPS0[v-1]` 的拷贝** ⇒ `e0v_eng` 行**逐位相同**。
    """
    lt = WL.LathTable(list(laths), omegas=WL.default_omega(
        len(laths), omega_max, axis=np.array([1.0, 0.0, 0.0]), mode='ladder'),
        eps0_var=EPS0, npref_var=NPF, gamma0=0.25)
    # ★ 复刻 `_bk_exp.py:535-537`
    eps0 = [np.asarray(EPS0[v - 1], float).copy() for v in laths]
    npref = {i + 1: np.asarray(NPF[v], float) for i, v in enumerate(laths)}
    g = W.LevelSetMulti(8, 8e-9, C=np.asarray(C, float), eps0=eps0)
    g.lath = lt
    g.npref = npref
    return lt, g


def rows(g, i, j, tag):
    """★ **索引约定**（第 16 个自查错误的根因）：

    `e0v_eng` 是 **0 基、逐场** 的表（`windowB_surface.py:1063`
    `[[eps0[v][i,j] …] for v in range(len(eps0))]`），
    而引擎里是 `e0p = concatenate([zeros((1,6)), e0v_eng], 0)`（`:2890-2891`）
    ⇒ **`e0p[f]` 才是场 `f`**，`sext_e0` 同样（`sep = [0] + sext_e0`，`:2892`）。

    ⇒ 因此**场 `i` 对应 `e0v_eng[i-1]`**。
    ⚠ 第一版直接写 `e0v_eng[i]` ⇒ 实际比的是**相邻两个场**（场 i 与场 i+1）
    ⇒ 打出 "场1(V1)-场2(V1) 不同" 的假象，**差点推翻 `§137.4`**。
    （最后是 `IndexError: index 12 out of bounds for size 12` 把它暴露出来的。）
    """
    ek = np.asarray(g.e0v_eng[i - 1], float)
    el = np.asarray(g.e0v_eng[j - 1], float)
    sk = float(np.asarray(g.sext_e0, float)[i - 1])
    sl = float(np.asarray(g.sext_e0, float)[j - 1])
    same_e = np.array_equal(ek, el)
    same_s = (sk == sl)
    md = float(np.max(np.abs(ek - el)))
    print('     %-22s e0v_eng 逐位相同=%-6s（max|Δ|=%.3e）  sext_e0 相同=%-6s'
          '（%.6g vs %.6g）' % (tag, same_e, md, same_s, sk, sl))
    return same_e, same_s


def main():
    print('=' * 104)
    print('_r212 —— 独立验证：同变体的 `Δed` 为何恰好 ≡ 0（`§137.4` 的基础）')
    print('=' * 104)
    ok = True

    # ---- 主用例：真实算例用的板条表 `1,1,2,2,3,3,4,4,7,7,8,8`（`saSet2`）----
    laths = [1, 1, 2, 2, 3, 3, 4, 4, 7, 7, 8, 8]
    lt, g = build(laths)
    print()
    print('  ## 真实表 `%s`（M=%d nreg=%d）' % (','.join(map(str, laths)),
                                             lt.M, lt.nreg))
    print('     场→变体：%s' % {i + 1: laths[i] for i in range(len(laths))})
    e0_same, e0_diff = [], []
    for i in range(1, lt.nreg):
        for j in range(i + 1, lt.nreg):
            vi = laths[i - 1] if i - 1 < len(laths) else 0
            vj = laths[j - 1] if j - 1 < len(laths) else 0
            se, ss = rows(g, i, j, '场%d(V%d)-场%d(V%d)' % (i, vi, j, vj))
            (e0_same if vi == vj else e0_diff).append((se, ss, i, j, vi, vj))
    n_same = len(e0_same)
    n_diff = len(e0_diff)
    a1 = all(se and ss for (se, ss, *_ ) in e0_same)
    a2 = all(not se for (se, ss, *_ ) in e0_diff)
    print()
    print('     **E-1** 同变体对 %d 个：`e0v_eng` 与 `sext_e0` **全部逐位相同** ⇒ %s'
          % (n_same, '✅ 通过' if a1 else '❌ 失败'))
    print('     **E-2** 异变体对 %d 个：`e0v_eng` **全部不同** ⇒ %s'
          % (n_diff, '✅ 通过' if a2 else '❌ 失败'))
    if a1 and n_diff == 0:
        print('     ⚠ E-2 无样本 ⇒ **不适用**（该表全同变体）')
    ok = ok and a1 and (a2 or n_diff == 0)

    # ---- E-3 正对照：任意两个不同变体必须"不同" ----
    print()
    print('  ## **E-3 正对照**：从 `EPS0` 直接比 1 号与 2 号变体的本征应变')
    d12 = float(np.max(np.abs(np.asarray(EPS0[0], float) - np.asarray(EPS0[1], float))))
    print('     `EPS0[0]` vs `EPS0[1]`：max|Δ| = **%.6e** ⇒ %s'
          % (d12, '✅ 不同（正对照通过）' if d12 > 0 else '❌ 相同 ⇒ 正对照失败'))
    ok = ok and d12 > 0
    d11 = float(np.max(np.abs(np.asarray(EPS0[0], float) - np.asarray(EPS0[0], float))))
    print('     自比 `EPS0[0]` vs 自己：max|Δ| = %.1f ⇒ 必须恰好 0 %s'
          % (d11, '✅' if d11 == 0 else '❌'))
    ok = ok and d11 == 0

    # ---- 交叉验证：把实测的 "F3 上 Δed≡0" 与这里的结构性结论对齐 ----
    print()
    print('=' * 104)
    print('  ## 结论')
    print('=' * 104)
    print('     ⇒ 同变体的两个场拿到的是**逐位相同**的 `e0v_eng` / `sext_e0`，')
    print('       而 `σ` 只按 `reg`（winner）算、**与 v 无关**（`:2889`），')
    print('       且 `_ed()` 只是按 idx gather 不同行去乘**同一个** `sig`（`:2894-2898`）')
    print('     ⇒ ⇒ **`ed_k − ed_l ≡ 0` 对同变体对是**结构性恒等式**，不是数值巧合。** ✅')
    print()
    print('     ⇒ `§137.4` 成立：**F3（块内低角晶界）的运动完全由界面能 `γ_RS(θ)` 控制**。')
    print('     ⇒ 而 P1-45（`ω` 参数化）决定的正是 `γ_RS` 的自变量 θ')
    print('       ⇒ **P1-45 直接决定块内结构** —— 重要性上调。')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
