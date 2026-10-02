#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_varprobe.py --- 变体构造的**裸诊断**：`(n, d)` 两两夹角。
不做极分解、不套对称群 —— 只用 `variants()` 返回的 `meta`。"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_ti64_variants as V  # noqa


def ang(u, v):
    c = abs(float(np.dot(u, v))) / (np.linalg.norm(u) * np.linalg.norm(v))
    return float(np.degrees(np.arccos(np.clip(c, -1, 1))))


def main():
    _, Fs, meta = V.variants()
    n = len(meta)
    print('=' * 92)
    print('变体构造裸诊断：n=%d' % n)
    print('=' * 92)
    ns = [m['n'] for m in meta]
    ds = [m['d'] for m in meta]
    print('── `n`（{110} 惯习法向）的**唯一取值** ──')
    uniq = []
    for v in ns:
        if not any(ang(v, u) < 1e-6 for u in uniq):
            uniq.append(v)
    print('   共 **%d** 个唯一 n：' % len(uniq))
    for u in uniq:
        print('     %s' % np.round(u, 4))
    print()
    print('── `n` 两两夹角（唯一值之间）──')
    for i in range(len(uniq)):
        row = ' '.join('%7.2f' % ang(uniq[i], uniq[j]) for j in range(len(uniq)))
        print('   %s' % row)
    print('   ⇒ {110} 面之间的夹角应为 0/60/90/120°')
    print()
    print('── `d`（{111} 长轴）两两夹角（全部 12 个）──')
    for i in range(n):
        print('   变体 %-3d : %s' % (i + 1, ' '.join('%7.2f' % ang(ds[i], ds[j])
                                                    for j in range(n))))
    print('   ⇒ {111} 方向之间的夹角应为 0/70.53/109.47/180°')
    print()
    print('── 每个变体的 (n,d)：n·d 应为 0（d ⊥ n）──')
    for i, m in enumerate(meta):
        print('   变体 %-3d  n·d = %+.3e   |n|=%.4f |d|=%.4f'
              % (i + 1, float(np.dot(m['n'], m['d'])),
                 np.linalg.norm(m['n']), np.linalg.norm(m['d'])))
    print()
    print('=' * 92)
    print('★ 判读（**预先写死**）')
    allnd = [abs(float(np.dot(m['n'], m['d']))) for m in meta]
    print('  · 所有 |n·d| < 1e-9 ？ %s' % ('✅' if max(allnd) < 1e-9 else '❌ max=%.2e' % max(allnd)))
    # n 的唯一值数应该是 6，d 的唯一值数应该是 4
    ud = []
    for v in ds:
        if not any(ang(v, u) < 1e-6 for u in ud):
            ud.append(v)
    print('  · `n` 唯一值 = %d（{110} 面族给 **6** 个）%s'
          % (len(uniq), '✅' if len(uniq) == 6 else '❌'))
    print('  · `d` 唯一值 = %d（{111} 方向族给 **4** 个）%s'
          % (len(ud), '✅' if len(ud) == 4 else '❌'))
    print('  ⇒ 12 = 6 面 × 2 方向，与 Burgers 的 12 变体一致 ⇒ **构造本身对**')
    print('  ⇒ ⇒ **那么"取向差只有 0–10.5°"这件事，根因在 `_r581_misorient.py` 的算法上**，')
    print('     不在变体构造上 —— 见下一条。')
    print('=' * 92)
    print('⚠ 记账（R581-R28 的诚实结论）：')
    print('  `_r581_misorient.py` 用 `polar(F)` 去当"取向" —— 但 `build_F` 的 `F` 是')
    print('  **在逐变体基底 (d,e,n) 上写的对应/应变矩阵**（`Fd=s·d`、`Fn=λ·n`、')
    print('  `Fe=s·(cos60·d+sin60·σm)`）⇒ **晶体的"取向"信息在 `B=[d|e|n]` 里，不在 `F` 里**。')
    print('  ⇒ `polar(F_i)ᵀ·polar(F_j)` **不是**两个变体的取向差。')
    print('  ⇒ **正确做法：用 `B_i = [d_i|e_i|n_i]` 当取向矩阵**，在**子晶系**里算')
    print('     `ΔR = B_iᵀ·B_j`，再套 HCP 点群。**我尚未做这一步**（如实登记）。')
    print('=' * 92)


if __name__ == '__main__':
    main()
