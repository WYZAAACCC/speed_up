#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r129_branch.py —— `§93` 的**重新定性**：两条选支准则的完整对照。

## 关键事实（刚查到，**改变了 `§93` 的问题本身**）

`T16_verify_rve.py:50-53`：
```python
from windowB_pf3d import argmin_normal as _argmin_normal
NPF[v + 1] = _argmin_normal(C, np.asarray(EPS0[v], float))[0]
```
⇒ **`NPF[v]` = `argmin_n 0.5·ε:Lam(C,n):ε`（弹性能泛函的极小法向）**，
**不是**晶体学的惯习面法向。
⇒ 所以 `§93` 原来的问法（"`NPF` 是不是惯习面法向"）**前提就不对**。

而 `_rank1_axes(E, nref)` 把 `NPF` 当 **`nref`** 用来在**两个 rank-1 分支**里选一个
（`n⁺ = e1 + r·e3` 与 `n⁻ ∝ a⁺`）。**真正决定板条厚向的是这个"选支"**，不是 `NPF` 本身。

## 本脚本报什么（每个变体）

| 量 | 含义 |
|---|---|
| `rB(n*)` / `rB(a)` | "平面 ⟂u 内向量不动"的残差（不变平面判据；`_r94` 已过正对照） |
| **`E(n*)` / `E(a)`** | 两个 rank-1 分支的**弹性能泛函值**（`0.5 ε:Lam(C,n):ε`） |
| `argmin rB` | **结构**判据选谁 |
| `argmin E` | **弹性能**判据选谁（≈ 现行代码的选法） |

⇒ 若两者对某些变体选**不同分支**，且**弹性能差很小而 `rB` 差很大**，
则现行选支规则在那些变体上**判据分辨力不足**（`_chk_habit5.py:17` 自己实测"只差 8.6%"）。

⚠ **本脚本不下"该改代码"的结论** —— 那是物理前提，需用户/专家裁定。
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import windowB_surface as WS                                 # noqa: E402
from windowB_pf3d import C_cubic, _lam_full                  # noqa: E402
from T16_verify_rve import EPS0, NPF                        # noqa: E402

C = C_cubic(134.0e9, 110.0e9, 36.0e9)


def npf(v):
    try:
        return np.asarray(NPF[v], float)
    except (KeyError, IndexError):
        return np.asarray(NPF[v - 1], float)


def rB(F, u):
    u = np.asarray(u, float); u = u / np.linalg.norm(u)
    t = np.array([1.0, 0.0, 0.0]) if abs(u[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    b1 = np.cross(u, t); b1 /= np.linalg.norm(b1)
    b2 = np.cross(u, b1)
    return float(np.linalg.norm((np.asarray(F, float) - np.eye(3))
                                @ np.stack([b1, b2], 1), 2))


def Efun(e, n):
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    e = np.asarray(e, float)
    return 0.5 * float(np.einsum('ij,ijkl,kl->', e, _lam_full(C, n), e))


def branches(e):
    """`_rank1_axes` 的**两个**候选（不选支）。返回 `[(n,a), ...]`。"""
    w_, V = np.linalg.eigh(np.asarray(e, float))
    o = np.argsort(w_)[::-1]
    w_ = w_[o]; V = V[:, o]
    mu1, mu3 = w_[0], w_[2]
    if mu1 <= 0 or mu3 >= 0:
        return []
    e1, e3 = V[:, 0], V[:, 2]
    r = np.sqrt(-mu3 / mu1)
    out = []
    for sgn in (+1.0, -1.0):
        n = e1 + sgn * r * e3
        n = n / np.linalg.norm(n)
        a = mu1 * e1 - sgn * np.sqrt(-mu1 * mu3) * e3
        a = a / np.linalg.norm(a)
        out.append((n, a))
    return out


def main():
    from windowB_ti64_variants import variants
    _E, FV, _M = variants()
    print('=' * 116)
    print('_r129 —— 两条选支准则对照（**结构**：`argmin rB`  vs  **弹性能**：`argmin E`）')
    print('=' * 116)
    print('  %-4s %-11s %-11s %-13s %-13s %-9s %-9s %s'
          % ('变体', 'rB(分支1)', 'rB(分支2)', 'E(分支1)(J/m³)', 'E(分支2)',
             'rB选', 'E选', '一致？'))
    n_dis = 0
    for v in range(1, 13):
        e = np.asarray(EPS0[v - 1], float)
        F = np.asarray(FV[v - 1], float)
        bs = branches(e)
        if not bs:
            print('  V%-3d （无 rank-1 分支）' % v)
            continue
        # 哪一个分支是代码实际用的（`n` 更接近 `NPF`）
        nref = npf(v); nref = nref / np.linalg.norm(nref)
        d = [abs(float(n @ nref)) for n, _ in bs]
        cur = int(np.argmax(d))
        rb = [rB(F, n) for n, _ in bs]
        ee = [Efun(e, n) for n, _ in bs]
        win_rb = int(np.argmin(rb))
        win_e = int(np.argmin(ee))
        same = (win_rb == win_e)
        n_dis += int(not same)
        print('  V%-3d %-11.4e %-11.4e %-13.4e %-13.4e %-9s %-9s %s'
              % (v, rb[0], rb[1], ee[0], ee[1],
                 '分支%d' % (win_rb + 1), '分支%d' % (win_e + 1),
                 '✅ 一致' if same else '⚠ **不一致**'))
    print()
    print('  ⇒ **两条准则选不同分支的变体数 = %d/12**' % n_dis)
    print()
    print('  ---- 记账 ----')
    print('  * 现行代码用 `nref = argmin_normal(C, ε)`（= **弹性能**）来选支')
    print('    （`windowB_surface.py:1116`）⇒ 对应上表的"E选"列。')
    print('  * `_chk_habit5.py:17` 自己实测：**两个 rank-1 分支的弹性能只差 8.6%**')
    print('    ⇒ 弹性能判据的**分辨力弱**。')
    print('  * 而 `rB` 的分离度见上表（很多变体上差 1–2 个数量级）⇒ 分辨力**强**。')
    print('  * ⚠ 但"惯习面 = 不变平面"是**晶体学**要求，而模型是**弹性能**框架；')
    print('    在 `F` **不是精确 IPS**（`|λ−1| = 4.17e-4`）时两者**本来就可能不同**。')
    print('    ⇒ **哪一个才是对的，是物理前提问题，不由本脚本裁定。**')
    return 0


if __name__ == '__main__':
    sys.exit(main())
