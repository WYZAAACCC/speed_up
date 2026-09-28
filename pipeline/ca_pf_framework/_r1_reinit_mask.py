#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_reinit_mask.py --- R1 reinit 审计（第 10 步）：**判据掩模选错了吗？**

动机（`_r1_reinit_deg.py` Phase 2 逼出来的）
-------------------------------------------
在**真正退化**的场上（配置 D，200 步，`med_in = 0.88554`），Sussman 迭代把带内
`median|∇d2|` **单调越做越低**（0.886 → 0.878@36 → 0.861@100 → 0.844@150），
**没有任何 iters 能恢复到 1±0.02**；同时 `flips ≤ 11/21280`、`dV ∈ [−3,+4]`
⇒ 界面**几乎没动**，改的是**斜率的分布**。

主假设（本文件直接可证伪）：
  `d2 = 0.5(φ_k − φ_l)` 的零等值面**不止一处** —— 除了真正的 (k,l) 界面，
  还有大量 `φ_k = φ_l` 的**伪交点**（多区域 VDF 里 φ_0 = −min_j φ_j，
  远离该配对处 φ_0 与 φ_l 会在别的地方相等）。
  `reinitialize()` 的**跳过判据**（`windowB_surface.py:3313`）与
  `_sussman_core` 的统计量 `_gm`/`_gmax`（`:261`/`:284`）用的都是
  **`|d2| ≤ band·dx` 的全带宽掩模** ⇒ 把这些伪交点也算了进去；
  而**回写**用的是 `corr2 = np.where(is_kl, corr2, 0.0)`（`:3338`），
  `is_kl` = "该胞的 `(argmin, argmin₂)` 正好是 (k,l)" —— **两把尺子不是同一把**。

做法（★ 只读：本文件**不构造 `LevelSetMulti`**，只用冻结的 `phi` 直接算）
  1. 同一对 `d2`，分别在
       `near`        = `|d2| ≤ band·dx`            （引擎判据用的掩模）
       `near & is_kl`= 再加"该胞确实属于这一对"   （引擎回写用的掩模）
       ` |d2| ≤ 1.5dx`（更薄的壳，作第三把尺子）
     上量 `median|∇d2|`（中心差分，与引擎告警同口径）。
  2. 报 `|near & is_kl| / |near|`（被伪交点污染的比例）与两者的中位差。
  3. 若 `near & is_kl` 上的中位 ≈ 1 而 `near` 上的明显偏低 ⇒ **假设成立**，
     且**改动点明确**：跳过判据与统计量应改用 `near & is_kl`。
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 6.0
TAGCFG = {'C1': (96 * 250e-9, 250e-9), 'C2': (96 * 125e-9, 125e-9)}


def gcen(f, dx):
    g = np.gradient(f, dx, edge_order=2)
    return np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)


def main():
    z = np.load(os.path.join(HERE, '_r1_reinit_states.npz'))
    print('=' * 118)
    print('R1 reinit 审计 / 判据掩模：`|d2| ≤ 6dx`  vs  `|d2| ≤ 6dx 且该胞属于这一对`')
    print('=' * 118)
    print('  %-8s %-11s %9s %9s %9s %9s %9s %9s %9s'
          % ('state', 'pair', '|near|', '|near&kl|', 'kl/near',
             'med@near', 'med@kl', 'med@1.5', 'med@3'))
    for key in sorted(z.files):
        phi = z[key]
        tag = key.split('_')[0]
        dx = TAGCFG[tag][1]
        nreg = phi.shape[0]
        order = np.argsort(phi, axis=0)
        ka, la = order[0], order[1]
        reg = ka.astype(np.int8)
        pairs = set()
        for ax in range(3):
            a = reg
            b = np.roll(reg, -1, axis=ax)
            sel = a != b
            if sel.any():
                for x, y in zip(a[sel].ravel(), b[sel].ravel()):
                    if x != y:
                        pairs.add((int(min(x, y)), int(max(x, y))))
        cand = []
        for (k, l) in sorted(pairs):
            d2 = 0.5 * (phi[k] - phi[l])
            n = int((np.abs(d2) <= BAND * dx).sum())
            cand.append((n, k, l))
        cand.sort(reverse=True)
        for (n, k, l) in cand[:3]:
            d2 = 0.5 * (phi[k] - phi[l])
            gn = gcen(d2, dx)
            near = np.abs(d2) <= BAND * dx
            is_kl = ((ka == k) & (la == l)) | ((ka == l) & (la == k))
            m_kl = near & is_kl
            thin = np.abs(d2) <= 1.5 * dx
            thin3 = np.abs(d2) <= 3.0 * dx
            f_ = lambda m: (float(np.median(gn[m])) if m.any() else np.nan)
            print('  %-8s (%2d,%2d)   %9d %9d %8.3f%% %9.5f %9.5f %9.5f %9.5f'
                  % (key, k, l, n, int(m_kl.sum()),
                     100.0 * m_kl.sum() / max(n, 1), f_(near), f_(m_kl),
                     f_(thin), f_(thin3)), flush=True)
    print()
    print('  ★ 判读：若 `med@kl` ≈ 1 而 `med@near` 明显偏低 ⇒ 引擎的跳过判据/统计量')
    print('    被**伪零交点**污染，应改用"`|d2| ≤ band·dx` **且** `is_kl`"（= 回写用的同一把尺子）。')
    print('=' * 118)
    return 0


if __name__ == '__main__':
    sys.exit(main())
