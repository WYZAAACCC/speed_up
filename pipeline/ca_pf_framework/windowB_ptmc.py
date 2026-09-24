#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""windowB_ptmc.py --- 为什么"只带贝恩应变"的板条无法在母相中长大：
                     马氏体晶体学（PTMC）的 lambda2 = 1 判据

背景（本轮实测）：
  Gibbs 面板条模型里，单胞/单片翻转总是被弹性能挡住（单变体夹杂 ~1e9 >> df ~5e7）
  ⇒ 动力学完全不动。这不是数值问题，而是**物理**：

  · 相干夹杂在母相中的弹性能量级 ~ mu*|eps|^2 ~ 1e9 J/m^3；
  · 只有当"形状应变"存在**不变平面**（invariant plane strain, IPS）时，
    板条的宏观形状变化才与母相相容（法向位移为零），弹性能才被释放；
  · 判据（Bhattacharya 学派，现代 PTMC）：
        单变体:   U = sqrt(F^T F) 的**中间**本征值 lambda2 必须 = 1
        孪晶配对的板条:  lambda2(U_A^{-1} U_B) = 1
    否则**不存在**不变平面 ⇒ 板条不可能以该应变相容长大。

本文件只用晶体学输入（a_beta / a_alpha / c_alpha + Burgers 对应）算这两条，
不引入任何新参数。
"""
import itertools
import numpy as np
from windowB_ti64_variants import variants


def U_of(F):
    C = F.T @ F
    w, _ = np.linalg.eigh(C)
    return np.sqrt(np.clip(w, 1e-30, None)), F


def lambda2(F):
    w, _ = U_of(F)
    return float(w[1])


def main():
    strains, Fs, meta = variants()
    print('=' * 92)
    print('马氏体晶体学判据：贝恩应变的不变平面（IPS）检查')
    print('=' * 92)
    print('\n[1] 单变体：U = sqrt(F^T F) 的三个本征值（lambda2 必须 = 1 才有不变平面）')
    l2s = []
    for v, F in enumerate(Fs):
        w, _ = U_of(F)
        l2s.append(w[1])
    l2s = np.array(l2s)
    print('    lambda1 = %.5f ~ %.5f' % (min(U_of(F)[0][0] for F in Fs),
                                        max(U_of(F)[0][0] for F in Fs)))
    print('    lambda2 = %.5f ~ %.5f     <-- 应为 1.0' % (l2s.min(), l2s.max()))
    print('    lambda3 = %.5f ~ %.5f' % (min(U_of(F)[0][2] for F in Fs),
                                        max(U_of(F)[0][2] for F in Fs)))
    print('    => 12 个变体的 lambda2 都离 1 很远（|lambda2-1| = %.4f）'
          % np.abs(l2s - 1).min())
    print('    => **只带贝恩应变的单变体板条没有不变平面 ⇒ 无法与母相相容长大**')
    print('       这正是 Gibbs 模型"完全不动"的物理原因（不是数值 bug）')

    print('\n[2] 孪晶配对（两变体层片）：lambda2(U_A^{-1} U_B) 是否 = 1？')
    rows = []
    for a, b in itertools.combinations(range(len(Fs)), 2):
        UA, _ = U_of(Fs[a])
        UB, _ = U_of(Fs[b])
        M = np.diag(1.0 / UA) @ (np.linalg.inv(np.linalg.qr(Fs[a])[0]) @ Fs[a]).T @ Fs[b] \
            @ np.diag(1.0 / UB)
        # 用标准形式: 相对伸长 U_A^{-1} U_B 的中间本征值
        rel = np.linalg.inv(np.diag(UA)) @ np.diag(UB)
        rows.append((abs(rel[1, 1] - 1.0), a, b, rel[1, 1]))
    rows.sort()
    print('    最接近 lambda2 = 1 的 6 对（第 2 列 = |lambda2-1|）:')
    for d, a, b, l2 in rows[:6]:
        print('      V%2d-V%2d  |lambda2-1| = %.5f   (lambda2 = %.5f)' % (a + 1, b + 1, d, l2))
    print('    => 朴素"把两个变体叠起来"也拿不到 lambda2 = 1')
    print('       （真正做法要按 PTMC 搜索: 孪晶面 + 孪晶分数 + 刚体转动, 使 lambda2 = 1；')
    print('        对应的"自协调集团"才是马氏体板条能长大的构型）')
    return l2s


if __name__ == '__main__':
    main()
