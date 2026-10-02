#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_null.py --- ★★★★★★★ **C6 的判决：`r_selfac` 有没有**超出随机混合**的信号？**

## 公式（`_bk_measure.py:493-504`，**逐字读出来的**）
```python
E[i] = dev(eps0_var[i])                    # 每个变体的**偏应变**
scale = mean(‖E[i]‖_F for i in 0..11)      # 归一化尺度
acc  = Σ_v (vols[v]/tot) * E[v-1]          # **按体积分数加权的向量和**
r_selfac = ‖acc‖_F / scale
```
**⇒ ⇒ **★ 所以 `r_selfac` 就是"**加权和的模**"**：
> **`r_selfac` = 1** ⇔ **单变体**（或所有 `E` 同向）；
> **`r_selfac` → 0** ⇔ **加权和互相抵消**。

## ★★★ 为什么必须配**零模型**（本轮的核心）
**把若干**不同取向**的 `E` 加权相加，**模**几乎总会变小****（**像随机游走**）⇒
**⇒ **∴ `r_selfac` < 1 **本身不能**证明"自协调"**** ——
**它只证明"不是单变体"**。**自协调（self-accommodation）的物理含义是**特定变体对**互相抵消**，
而那要求 `r_selfac` **明显低于**同 `f_var` 下**随机混合**的期望**。

## 零模型（**随机取向**）
**若 12 个 `E_v` 的取向在 5 维偏应变空间里**近似正交**（各向同性）** ⇒
**E[‖Σ f_v E_v‖²] = (Σ f_v²) · ‖E‖²**（**因为交叉项期望为 0**）
⇒ **`r_null` = sqrt(Σ_v f_v²)**
（**等下用**实测的 `f_var` 算，并与实测 `r_selfac` 比**）
"""
import csv
import json
import os
import sys

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else '_exp/_bk_blk'
TAG = sys.argv[2] if len(sys.argv) > 2 else 'BK6'


def main():
    p = os.path.join(ROOT, 'dry_' + TAG, 'series.csv')
    if not os.path.exists(p):
        print('  ⚠ 没有 %s' % p)
        return
    rows = list(csv.DictReader(open(p, encoding='utf-8', errors='replace')))
    print('=' * 98)
    print('臂 %s：`r_selfac` vs **随机混合零模型** sqrt(Σ f_v²)' % TAG)
    print('=' * 98)
    print('  %-5s %-9s %-9s %-9s %s' % ('step', 'r_selfac', 'r_null', '比值', 'f_var（前 6 个非零）'))
    print('  ' + '-' * 94)
    for r in rows:
        rs = (r.get('r_selfac', '') or '').strip()
        fv = (r.get('f_var', '') or '').strip()
        if rs in ('', 'nan') or fv == '':
            continue
        try:
            r_self = float(rs)
        except Exception:
            continue
        parts = []
        for x in fv.split('/'):
            try:
                parts.append(float(x))
            except Exception:
                parts.append(0.0)
        s2 = sum(x * x for x in parts)
        r_null = float(np.sqrt(s2)) if s2 > 0 else float('nan')
        ratio = r_self / r_null if r_null > 0 else float('nan')
        nz = [('%.3f' % x) for x in parts if x > 1e-9][:6]
        print('  %-5s %-9.4f %-9.4f %-9.4f %s'
              % (r.get(list(r.keys())[0]), r_self, r_null, ratio, ','.join(nz)))
    print()
    print('  ★ 判读（**预先写死**）：')
    print('   · **r_selfac ≈ r_null**（比值 ≈1）⇒ **只是随机混合** ⇒ **C6 不成立**')
    print('   · **r_selfac 明显 < r_null**（比值 ≤0.7）⇒ **超出随机的抵消** ⇒ **C6 有信号**')
    print('   · **r_selfac ≈ 1** ⇒ **单变体（无混合）**')
    print()
    print('  ⚠ 零模型的**前提**：12 个 `dev(ε⁰)` 在偏应变空间里**近似各向同性**')
    print('     ⇒ **本轮**未独立验证**它（要用真实 `EPS0` 算交叉项）⇒ 标【推理】')
    print('=' * 98)


if __name__ == '__main__':
    main()
