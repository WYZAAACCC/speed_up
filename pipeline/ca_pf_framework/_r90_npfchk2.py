#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r90_npfchk2.py —— **`NPF` 惯习面法向表的正确校验**（`_r89` 的更正版）。

## `_r89` 错在哪（**必须先说清楚，否则会留下一个假结论**）

`_r89` 用 `F = I + EPS0_T16` 造形变梯度，得 `|λ−1| = 4.17e-4`（**12 个变体全一样**），
并且解析不变平面法向与 `NPF` 的夹角 **12/12 都是精确的 90.00°**。

> **12 个变体给出同一个 90.00°，是"我的判据错了"的指纹，不是"12 个变体都错"的证据。**

实证：本仓库 `_chk_habit5.py:22,104` 早就立过判据
**H-9 `|λ−1| < 1e-9`**（"构造保证"），并用的是
`windowB_ti64_variants.variants()` 返回的**真形变梯度 `FV`**。
⇒ `F = I + EPS0` **不是**那个 `F`（`EPS0` 是**小应变**表示，重建不出 `F`）。
⇒ **`_r89` 的结论（"P1-40 成立、两张表不一致"）作废**，本脚本用正确的 `F` 重做。

## 判据（照抄 `_chk_habit5.py` 的 H-9/H-11，不另发明）

* **H-9**：`Fᵀ n = λ n` 的 `|λ−1|` 应 `< 1e-9` —— **不成立则本判据不适用**（先查这个！）
* **H-11**：`NPF[v]` 与 `n_inv`（`λ` 最接近 1 的左特征向量）的夹角
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from T16_verify_rve import NPF                               # noqa: E402
from windowB_ti64_variants import variants                   # noqa: E402

EPS0V, FV, _M = variants()
NV = len(FV)
PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12)]


def npf(v):
    try:
        a = np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        a = np.asarray(NPF[v - 1], float)
    return a / np.linalg.norm(a)


def ang(u, v):
    u = np.asarray(u, float) / np.linalg.norm(u)
    v = np.asarray(v, float) / np.linalg.norm(v)
    return float(np.degrees(np.arccos(np.clip(abs(float(u @ v)), -1.0, 1.0))))


def main():
    print('=' * 108)
    print('_r90_npfchk2 —— `NPF` vs `Fᵀn = λn`（用**真形变梯度 `FV`**；H-9 先行）')
    print('=' * 108)
    ninv = {}
    worst_lam = 0.0
    for k in range(1, NV + 1):
        F = np.asarray(FV[k - 1], float)
        ev, evec = np.linalg.eig(F.T)
        ev = np.real(ev)
        j = int(np.argmin(np.abs(ev - 1.0)))
        v = np.real(evec[:, j])
        ninv[k] = v / np.linalg.norm(v)
        worst_lam = max(worst_lam, abs(float(ev[j]) - 1.0))
    print('  **H-9  `|λ−1|` 最大 = %.3e**（判据 < 1e-9）⇒ %s'
          % (worst_lam, 'PASS：不变平面存在，判据适用' if worst_lam < 1e-9
             else '**FAIL：判据不适用，下面的角度不能用来判 NPF**'))
    print()
    print('  %-4s %-12s %-34s %s' % ('变体', '|λ−1|', '∠(NPF[v], n_inv)', '判定'))
    angs = []
    for k in range(1, NV + 1):
        F = np.asarray(FV[k - 1], float)
        ev = np.real(np.linalg.eigvals(F.T))
        j = int(np.argmin(np.abs(ev - 1.0)))
        a = ang(npf(k), ninv[k])
        angs.append(a)
        print('  V%-3d %-12.2e %-34.2f %s'
              % (k, abs(float(ev[j]) - 1.0), a, '✅' if a < 2.0 else '❌'))
    print()
    print('  **H-11 `NPF` 离解析不变平面法向：max %.2f°  mean %.2f°  （>20° 的变体 %d/12）**'
          % (max(angs), float(np.mean(angs)), sum(1 for a in angs if a > 20)))
    if max(angs) < 2.0:
        print('     ⇒ ✅ **`NPF` 就是不变平面（惯习面）法向，逐变体正确。**')
    else:
        print('     ⇒ ⚠ 有变体不符 —— 需逐个查（**不要**像 `_r89` 那样只看整体）。')
    # ---- 对级：共享惯习面 ----
    print()
    print('=' * 108)
    print('  对级：`EPS0` 的组合配对 vs `NPF`/`n_inv` 的夹角（共享惯习面 ⇒ |n_k·n_l| ≈ 1）')
    print('=' * 108)
    print('  %-10s %-14s %-14s %-12s %s'
          % ('对（EPS0）', '|NPF_k·NPF_l|', '|ninv_k·ninv_l|', 'r_pair', '共享惯习面？'))
    EV = [np.asarray(e, float) - np.trace(e) / 3.0 * np.eye(3) for e in EPS0V]
    nsh_npf = nsh_inv = 0
    for a, b in PAIRS:
        ca = float(npf(a) @ npf(b))
        ci = float(ninv[a] @ ninv[b])
        rp = (float(np.linalg.norm(EV[a - 1] + EV[b - 1]))
              / (np.linalg.norm(EV[a - 1]) + np.linalg.norm(EV[b - 1])))
        ok_a = abs(abs(ca) - 1.0) < 1e-3
        ok_i = abs(abs(ci) - 1.0) < 1e-3
        nsh_npf += int(ok_a)
        nsh_inv += int(ok_i)
        print('  (%2d,%2d)     %+-14.4f %+-14.4f %-12.4f NPF:%s  不变平面:%s'
              % (a, b, ca, ci, rp, '✅' if ok_a else '❌',
                 '✅' if ok_i else '❌'))
    print()
    print('  ⇒ `NPF` 下共享惯习面：%d/6；**不变平面法向下**共享：%d/6' % (nsh_npf, nsh_inv))
    print('  ⇒ 全部 66 对里 `|ninv_i·ninv_j| > 1-1e-3` 的对数：%d（应为 6）'
          % sum(1 for i in range(1, 13) for j in range(i + 1, 13)
                if abs(abs(float(ninv[i] @ ninv[j])) - 1.0) < 1e-3))
    return 0


if __name__ == '__main__':
    sys.exit(main())
