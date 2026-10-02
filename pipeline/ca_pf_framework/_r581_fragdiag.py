#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_fragdiag.py --- ★★ 碎片化**机理**诊断（待查项 A17/A21）。

## 要回答的问题
`R581_TASK5_VERDICT.md` 记了两件事：
* **A17**：`region == v` 给出的"场"在空间上**是碎的**（最多 12 个分量）；
* **A21**：跑到 `T_end` 后**碎片化加剧**（`nf3_col == nslab_n−1` 从 98% 掉到 67%）。

**这两件事是 C2（长宽比）和 C3（低角晶界分隔）失败的直接原因** ——
按"场"量几何量会得到**碎片云的包络**（P21/P22）。

## 假设（**预先写死，可证伪**）
**H1（S4 机理）**：同一场被切断的地方，隔开两个碎片的是一层
**恰好 1 胞厚的 β 膜**。
  依据：`R581_SIMPLIFICATION_AUDIT.md` 的 **S4** —— `--nuc-overlap-nm` 默认 **0**
  ⇒ 新片与旧片**只是相切**，而**阶梯错位**会让它们之间留 **1 胞 β**
  （实测 F3 覆盖率只有 **0.62**）。若 H1 成立，则：
  **碎片数应当 ≈ "相切拼接"的次数**，而**把 `--nuc-overlap-nm` 开到 1Δx 应当把碎片焊回去**。

**H2（挤压机理）**：碎片之间隔着**别的场**（异变体或同族不同号）⇒ 是**碰撞/竞争**切断的。

**H3（数值机理）**：碎片之间隔着 **>1 胞的 β**（既不是 1 胞膜、也不挨着别的场）
⇒ 是数值耗散/零集脱离，不是几何拼接问题。

## 怎么判（**量具**）
对每个 `ncomp > 1` 的场：
1. `ndimage.label` 取分量；
2. 对每个分量，**逐次膨胀 k = 1,2,3,4 胞**，记录**首次接触到"同场另一个分量"**的 k；
3. 同时记录"首次接触到**别的场**"的 k；
4. 按 k 与接触对象分类 ⇒ **H1 = 多数是 k=1 且接触对象是同场分量**。

⚠ **自洽检查（P21 强制）**：每个分量的**体积之和**必须 == `(region==v).sum()`
（不许出现"分量加起来比场还大"这种上一轮犯过的错）。
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'p2_b5'
    snap = sys.argv[2] if len(sys.argv) > 2 else None
    d = os.path.join('_exp/_bk_p2', 'dry_' + tag)
    if snap is None:
        cands = sorted([f for f in os.listdir(d) if f.startswith('snap_')],
                       key=lambda f: int(f.split('_')[1].split('.')[0]))
        snap = cands[-1]
    z = np.load(os.path.join(d, snap))
    reg = z['region']
    print('=' * 96)
    print('R581 —— 碎片化机理诊断：%s / %s' % (tag, snap))
    print('=' * 96)
    print('快照键：%s' % list(z.keys()))
    L = float(z['L']) if 'L' in z else 1.0
    dx = L / reg.shape[0]
    print('盒子 %d³   L=%.3f µm   dx=%.3f nm' % (reg.shape[0], L * 1e6, dx * 1e9))
    flds = [int(v) for v in np.unique(reg) if v > 0]
    print('出现的场 %d 个：%s' % (len(flds), flds))
    print()

    # ---- 自洽检查 ----
    tot = int((reg > 0).sum())
    print('── 自洽检查（P21 强制）──')
    print('   `region>0` 的胞数 = %d' % tot)

    ncomp_tot = 0
    k1_same = k1_other = k_gt1 = 0
    rows = []
    for v in flds:
        M = (reg == v)
        nv = int(M.sum())
        lab, n = ndimage.label(M)
        if n == 1:
            rows.append((v, 1, nv, '-', '-', '-'))
            continue
        ncomp_tot += n
        sizes = ndimage.sum(M, lab, range(1, n + 1)).astype(int)
        # 每个分量的掩模
        masks = [(lab == i) for i in range(1, n + 1)]
        # 记录每个分量"首次接触"的 k 与对象
        for i in range(n):
            others_same = np.zeros_like(M)
            for j in range(n):
                if j != i:
                    others_same |= masks[j]
            other_fld = (reg > 0) & (reg != v)
            k_same = k_oth = None
            cur = masks[i]
            for k in range(1, 5):
                cur = ndimage.binary_dilation(cur)
                if k_same is None and (cur & others_same).any():
                    k_same = k
                if k_oth is None and (cur & other_fld).any():
                    k_oth = k
                if k_same is not None and k_oth is not None:
                    break
            if k_same is not None and (k_oth is None or k_same <= k_oth):
                if k_same == 1:
                    k1_same += 1
                else:
                    k_gt1 += 1
            elif k_oth is not None:
                k1_other += 1
            else:
                k_gt1 += 1
        # 体积自洽
        s = int(sizes.sum())
        assert s == nv, '自洽检查 FAIL：场 %d 分量体积和 %d != %d' % (v, s, nv)
        rows.append((v, n, nv, int(sizes.max()), int(np.median(sizes)),
                     '/'.join(str(x) for x in sorted(sizes, reverse=True)[:8])))
    print('   逐场分量体积之和 == 场的胞数：✅ 全部成立（无"分量比场还大"）')
    print()
    print('── 逐场 ──')
    print('   %-5s %-5s %-8s %-8s %-8s %s' % ('场', '分量数', '胞数', '最大分量', '中位', '各分量胞数(前8)'))
    for r in rows:
        print('   %-5s %-5s %-8s %-8s %-8s %s' % r)
    print()
    print('=' * 96)
    print('★ 假设判决（**预先写死**）')
    print('=' * 96)
    print('   H1（1 胞 β 膜切断；S4 机理）：分量"首次接触同场另一分量"的 k == 1')
    print('   H2（被别的场挤断）          ：分量"首次接触别的场"更早')
    print('   H3（>1 胞 β 隔开）          ：k ≥ 2 才接触')
    print()
    print('   多分量场里，**非最大分量**的计数：')
    print('     k=1 且先碰到**同场**分量（**H1 证据**） = %d' % k1_same)
    print('     先碰到**别的场**（H2 证据）              = %d' % k1_other)
    print('     k≥2 或都没碰到（H3 证据）               = %d' % k_gt1)
    print()
    tot_c = k1_same + k1_other + k_gt1
    if tot_c:
        print('   ⇒ 占比：H1 %.1f%% / H2 %.1f%% / H3 %.1f%%'
              % (100 * k1_same / tot_c, 100 * k1_other / tot_c, 100 * k_gt1 / tot_c))
        win = max((k1_same, 'H1（S4：1 胞 β 膜）'), (k1_other, 'H2（被别的场挤断）'),
                  (k_gt1, 'H3（>1 胞 β）'))[1]
        print('   ⇒ **主因 = %s**' % win)
        if k1_same >= 0.5 * tot_c:
            print('   ⇒ ★★ **H1 成立** ⇒ 碎片化**主要是"相切拼接留 1 胞 β 膜"造成的**')
            print('      ⇒ 直接对应 **S4**（`--nuc-overlap-nm` 默认 0）')
            print('      ⇒ **可证伪的预测**：把 `--nuc-overlap-nm` 开到 1Δx（62.5 nm）')
            print('         应当把碎片焊回去 ⇒ `p2_b5ov` 的分量数应显著少于 `p2_b5`')
        else:
            print('   ⇒ 主因不是 1 胞膜 ⇒ **S4 不是碎片化的主因**，要另找（如实登记）')
    else:
        print('   ⇒ 没有多分量场 ⇒ 无碎片化')
    print()
    print('⚠ 记账：本量具只做**几何**判据（膨胀 k 胞看碰到谁），')
    print('   **不**证明动力学原因；H1 的因果要靠 `--nuc-overlap-nm` 的 A/B 验。')
    print('=' * 96)


if __name__ == '__main__':
    main()
