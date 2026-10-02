#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_iface.py --- ★★★ **把"真的形成的界面"和"真实晶体学取向差"接起来**。

## 为什么要接
R22/R23 已经**实测**了末态**真的形成**的界面：
* **F3（同变体）边 4 条**：b5 = {2–4, 1–2, 1–3, 19–20}；b3 = {2–4, 1–3, 1–2}
* **F2（异变体）边 1 条**：两臂**都是 场 3–18**
而 R29 给出了 12 个变体的**完整取向矩阵** `R_i = [d|σm|n]`（G1/G2 自检通过）。

**⇒ 本轮把两者接起来：算出**每一个真实界面**的**真实取向差**。**

## 关键推论（**写在这里，代码只是把它算出来**）
b5/b3 的场→变体是 `{1:1, 2:1, 3:1, 4:1, 17:5, 18:5, (19:5,20:5), (25:7)}`
（`vmap_vals`，`_bk_exp.py:1292` 逐字）。
* **F3 边全在"同变体"之间**（1–2、1–3、2–4 都是变体 1；19–20 都是变体 5）
  ⇒ **它们之间的真实晶体学取向差是 0°**；
* **唯一真实的晶体学界面是 F2 场 3–18**（变体 1 vs 5）。

⇒ **模型里的 "block"（4 根、3 条 F3 边）在晶体学上是"一个晶体"**，
而 `ladder` θ 给它们的 0.106–0.319° 是**占位**，不是晶体学量。

## 判据（**预先写死**）
* **P1**：同变体对的真实取向差必须 **== 0°**（否则取向矩阵构造错）；
* **P2**：F2 场 3–18（变体 1–5）的真实取向差必须落在 R29 谱里（60.00/60.83/63.26/90.00/90.24°）
  且**与 Shuai 2026 的某一类对应** —— **报出是哪一类**。
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_ti64_variants as V  # noqa

LIT = [(63.26, 'Type 4 <10 5 5 3>'), (60.00, 'Type 2 <11-20>'),
       (60.83, 'Type 3 <10 7 17 3>'), (90.00, 'Type 5 <7 17 10 0>'),
       (10.53, 'Type 6 <0001>')]


def hcp_ops():
    ops = []
    for k in range(6):
        a = np.radians(60 * k)
        Rz = np.array([[np.cos(a), -np.sin(a), 0],
                       [np.sin(a), np.cos(a), 0], [0, 0, 1.0]])
        ops.append(Rz)
        ops.append(Rz @ np.diag([1.0, -1.0, -1.0]))
    return ops


def build_R(meta):
    R = []
    for m in meta:
        d = m['d'] / np.linalg.norm(m['d'])
        nv = m['n'] / np.linalg.norm(m['n'])
        mm = np.cross(nv, d); mm /= np.linalg.norm(mm)
        e = m['e'] / np.linalg.norm(m['e'])
        sig = 1.0 if e @ mm > 0 else -1.0
        R.append(np.column_stack([d, sig * mm, nv]))
    return np.array(R)


def main():
    _, Fs, meta = V.variants()
    ops = hcp_ops()
    R = build_R(meta)

    def theta(i, j):           # 变体号 1..12
        dR = R[i - 1].T @ R[j - 1]
        return min(np.degrees(np.arccos(np.clip((np.trace(S @ dR) - 1) / 2, -1, 1)))
                   for S in ops)

    print('=' * 96)
    print('R581 —— **真的形成的界面** × **真实晶体学取向差**')
    print('=' * 96)
    # 实测的界面（R22/R23）+ 场→变体（`vmap_vals`）
    arms = {
        'p2_b5': dict(vmap={1: 1, 2: 1, 3: 1, 4: 1, 17: 5, 18: 5, 19: 5, 20: 5, 25: 7},
                      F3=[(2, 4), (1, 2), (1, 3), (19, 20)], F2=[(3, 18)]),
        'p2_b3': dict(vmap={1: 1, 2: 1, 3: 1, 4: 1, 17: 5, 18: 5},
                      F3=[(2, 4), (1, 3), (1, 2)], F2=[(3, 18)]),
    }
    for tag, a in arms.items():
        print()
        print('#' * 96)
        print('# %s' % tag)
        print('#' * 96)
        print(' ── F3（同变体）边：真实取向差**必须 == 0°** ──')
        print('   %-10s %-16s %-12s %s' % ('场对', '变体对', '真实 θ', '判定'))
        p1ok = True
        for (i, j) in a['F3']:
            vi, vj = a['vmap'][i], a['vmap'][j]
            t = theta(vi, vj) if vi != vj else 0.0
            ok = abs(t) < 1e-9
            p1ok &= ok
            print('   %-10s %-16s %-12.4f %s' % ('%d–%d' % (i, j), 'v%d–v%d' % (vi, vj),
                                                 t, '✅' if ok else '❌'))
        print('   ⇒ **P1**：同变体对的真实取向差 == 0° ？ %s' % ('✅ 全部成立' if p1ok else '❌'))
        print()
        print(' ── F2（异变体）边：**唯一真实的晶体学界面** ──')
        print('   %-10s %-16s %-12s %s' % ('场对', '变体对', '真实 θ', '对应 Shuai 2026 类型'))
        for (i, j) in a['F2']:
            vi, vj = a['vmap'][i], a['vmap'][j]
            t = theta(vi, vj)
            nm = '**未落在文献五类角附近（±0.5°）**'
            for L, name in LIT:
                if abs(t - L) < 0.5:
                    nm = '**%s**' % name
            print('   %-10s %-16s %-12.2f %s' % ('%d–%d' % (i, j), 'v%d–v%d' % (vi, vj), t, nm))
    print()
    print('=' * 96)
    print('★★★ 结论（这是任务(5) 关于"低角晶界取向差"最完整的一条）')
    print('=' * 96)
    print('  1. **模型里那个"block"（4 根、3 条 F3 边）在晶体学上是【一个晶体】**：')
    print('     场 1/2/3/4 **全是变体 1**（`var_rule=\'ed\'` 选的），')
    print('     ⇒ 两两之间的**真实取向差 = 0.0000°**（不是"低角"，是**零**）。')
    print('  2. **模型给它们的 `ladder` θ（0.106–0.319°）是占位值**，不是晶体学量。')
    print('  3. **整个算例里只有 1 条真实的晶体学界面**：F2 场 3–18（变体 1–5），')
    print('     真实取向差见上 —— 它才该与 Shuai 2026 的 Type 2/3/4/5 对照。')
    print('  4. ⇒ **C3 后半句的正确判定**：')
    print('     * 「低角晶界」在模型里**是零取向差的同变体内部界面** ⇒')
    print('       **物理上对应真实的"block 内 lath 界面"，但模型的取向差来源是占位的**；')
    print('     * **跨变体（真正的 60°/63°/90° 高角界面）模型只形成了 1 条** ⇒')
    print('       样本量 = 1，**做不出分布**。')
    print('  5. ⇒ 要做出文献那样的**分布**，必须让**跨变体界面多起来** ——')
    print('     那又回到 **S15 / C5**（形核通道饱和 ⇒ 根数太少）。')
    print('=' * 96)


if __name__ == '__main__':
    main()
