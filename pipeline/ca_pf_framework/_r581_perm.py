#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_perm.py --- ★★★★★★★★ **C6 的判决实验（正确的零模型）：变体**标签置换检验****

## 为什么 R176 的零模型是**错的**
R176 我用 `r_null = sqrt(Σ_v f_v²)` 比。**但 `r_selfac` 本身就是**
`‖Σ_v f_v E_v‖/scale = sqrt(Σ_v Σ_w f_v f_w ⟨E_v,E_w⟩)/scale`
⇒ **给定 `f_var` 之后，`r_selfac` 是**确定量**，**没有随机性可谈**** ⇒
**⇒ **★ `sqrt(Σ f_v²)` 不是一个"零模型"，它是**另一个量**** ⇒ R176 的比值**没有意义**（**登记为更正**）。

## ★ 正确的零模型 = **标签置换**（permutation test）
**问法**：**同样的**体积分数多重集**，若**随机分给别的变体**，`r_selfac` 会是多少？**
* **观测值落在置换分布的**低尾**（如 ≤5% 分位）** ⇒ **★ "选中的是哪些变体"很关键** ⇒
  **变体选择**不是随机的**** ⇒ **支持 C6（有自协调的选variant机制）**；
* **观测值落在**中位附近**** ⇒ **★ 与"随机贴标签"无异** ⇒ **C6 不成立**（**所谓自协调只是混合的几何后果**）；
* **观测值落在**高尾**** ⇒ **比随机还差** ⇒ **反自协调**。

## 怎么算
1. 取**真实 `EPS0`**（12 个变体）⇒ `E_v = dev(EPS0[v-1])`；
2. 取观测的 `f_var`（**按变体号**的向量，含 0）⇒ 记 `f_v`；
3. **★ 置换**：把 `{f_v}` 这个**多重集**重新随机指派给 12 个变体（`np.random.permutation`），
   算 `r = ‖Σ_v f_π(v) E_v‖ / scale`；重复 N 次 ⇒ **得分布**；
4. 报**观测值的分位**（`p = P(r_perm ≤ r_obs)`）。
"""
import csv
import os
import sys

import numpy as np


def load_eps0():
    """从 `_bk_exp.py` 里拿 EPS0（12 个 3×3 张量）。"""
    sys.path.insert(0, os.getcwd())
    import importlib
    m = importlib.import_module('_bk_exp')
    E = getattr(m, 'EPS0', None)
    if E is None:
        raise RuntimeError('_bk_exp.EPS0 不存在')
    return [np.asarray(x, float) for x in E]


def dev(A):
    return A - np.trace(A) / 3.0 * np.eye(3)


def r_of(fvec, E):
    """r = ‖Σ_v f_v E_v‖_F / scale；`fvec` 长度 = len(E)。"""
    acc = np.zeros((3, 3))
    for v, f in enumerate(fvec):
        if f > 0:
            acc = acc + f * E[v]
    sc = float(np.mean([float(np.sqrt(np.sum(e ** 2))) for e in E]))
    return float(np.sqrt(np.sum(acc ** 2))) / (sc + 1e-300)


def main():
    ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
    TAG = sys.argv[2] if len(sys.argv) > 2 else 'BK6'
    NPERM = int(sys.argv[3]) if len(sys.argv) > 3 else 20000

    eps0 = load_eps0()
    E = [dev(A) for A in eps0]
    print('=' * 100)
    print('C6 判决：**变体标签置换检验**（臂 %s，%d 次置换）' % (TAG, NPERM))
    print('=' * 100)
    print('  EPS0：%d 个变体；dev 范数 = %s' %
          (len(E), np.array2string(np.array([np.sqrt(np.sum(e ** 2)) for e in E]),
                                   precision=4, max_line_width=200)))

    p = os.path.join(ROOT, 'dry_' + TAG, 'series.csv')
    if not os.path.exists(p):
        print('  ⚠ 没有 %s' % p)
        return
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    rng = np.random.default_rng(20261002)

    print()
    print('  %-5s %-10s %-10s %-10s %-9s %s'
          % ('step', 'r_selfac', '置换中位', '置换 5%', '★ p 值', '判决'))
    print('  ' + '-' * 94)
    for r in rows:
        rs = (r.get('r_selfac', '') or '').strip()
        fv = (r.get('f_var', '') or '').strip()
        if rs in ('', 'nan') or fv == '':
            continue
        try:
            r_obs = float(rs)
        except Exception:
            continue
        try:
            f = np.array([float(x) for x in fv.split('/')], float)
        except Exception:
            continue
        if len(f) < len(E):
            f = np.concatenate([f, np.zeros(len(E) - len(f))])
        f = f[:len(E)]
        s = f.sum()
        if s <= 0:
            continue
        f = f / s
        # 置换分布
        perm = np.empty(NPERM)
        idx = np.arange(len(E))
        for i in range(NPERM):
            pp = rng.permutation(idx)
            perm[i] = r_of(f[pp], E)
        pv = float(np.mean(perm <= r_obs))
        med = float(np.median(perm))
        q05 = float(np.percentile(perm, 5))
        if pv <= 0.05:
            verd = '★ **低于随机**（p≤0.05）⇒ 选变体非随机 ⇒ **支持 C6**'
        elif pv >= 0.95:
            verd = '★ 高于随机 ⇒ **反自协调**'
        else:
            verd = '⚠ **与随机标签无异** ⇒ **C6 不成立（或无法判定）**'
        print('  %-5s %-10.4f %-10.4f %-10.4f %-9.3f %s'
              % (r[list(r.keys())[0]], r_obs, med, q05, pv, verd))
    print()
    print('  ★ 判读（**预先写死**）：')
    print('   · **p ≤ 0.05**（观测 ≤ 置换分布的 5% 分位）⇒ **选中的变体很关键** ⇒ **C6 有支持**')
    print('   · **0.05 < p < 0.95** ⇒ **与随机贴标签无异** ⇒ **C6 不成立**')
    print('   · **p ≥ 0.95** ⇒ **比随机还差** ⇒ **反自协调**')
    print()
    print('  ⚠ 边界：置换保持**体积分数多重集**不变，只换"谁拿哪一份" ⇒')
    print('     它检验的是"**变体选择**"是否非随机，**不检验**"体积分数本身是否被弹性选择" ⇒ 已登记。')
    print('=' * 100)


if __name__ == '__main__':
    main()
