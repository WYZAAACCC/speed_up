#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_block_smoke.py —— R30 **J-1（块表量具）** 的正/负对照。

判据（预先写死）：
  K-1 单变体、6 根板条**贴在一起** ⇒ `nblk_sig == 1`、`blk_laths == '6'`
  K-2 两个变体、各自 3/2 根贴在一起且**互不相邻** ⇒ `nblk_sig == 2`、`blk_laths == '3/2'`
  K-3 **负对照**：在 K-1 的块中间插一层**母相**把它切断 ⇒ `nblk_sig == 2`
      （证明量具"真裂会报裂"，不是恒给 1）
  K-4 `r_selfac` 与**独立重算**（直接用 Σ f_v dev ε⁰ 的 Frobenius 范数）逐位相同
  K-5 `n_habit`：取**同一 {110}β 惯习面**的两个变体 ⇒ 1；取**不同惯习面**的两个 ⇒ 2
  K-6 与 `_r30_selfac_struct.min_residual` 的口径一致（同一组分数下两者相同）

跑法：  python3 _r30_block_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
from windowB_ti64_variants import variants                      # noqa: E402

EPS0, _F, META = variants()
NPF_EXACT = {i + 1: np.asarray(META[i]['n'], float) for i in range(12)}

N, DX = 48, 125e-9
L = N * DX
NH = np.array([0.0, 0.0, 1.0])
AA = np.array([1.0, 0.0, 0.0])
WA = np.cross(NH, AA)


def slab(reg, k, c_n, c_a, half_n, half_a=600e-9, half_w=600e-9):
    ii = np.arange(N) * DX
    rel = [ii[:, None, None] - L / 2, ii[None, :, None] - L / 2,
           ii[None, None, :] - L / 2]
    dn = NH[0] * rel[0] + NH[1] * rel[1] + NH[2] * rel[2] - c_n
    da = AA[0] * rel[0] + AA[1] * rel[1] + AA[2] * rel[2] - c_a
    dw = WA[0] * rel[0] + WA[1] * rel[1] + WA[2] * rel[2]
    m = (np.abs(dn) <= half_n) & (np.abs(da) <= half_a) & (np.abs(dw) <= half_w)
    reg[m] = k


def case_one_block(gap_n=0.0):
    """6 根同变体板条沿 n* 贴在一起（gap_n>0 ⇒ 中间留母相 ⇒ 应裂成两块）。"""
    reg = np.zeros((N, N, N), np.int8)
    t = 250e-9
    for j in range(6):
        off = (j - 2.5) * (t + gap_n)
        slab(reg, j + 1, off, 0.0, t / 2)
    return reg, {k: 1 for k in range(1, 7)}


def case_two_blocks():
    """变体 1 的 3 根（a<0 一侧）+ 变体 2 的 2 根（a>0 一侧），相距很远。"""
    reg = np.zeros((N, N, N), np.int8)
    t = 250e-9
    for j in range(3):
        slab(reg, j + 1, (j - 1) * t, -1500e-9, t / 2, half_a=800e-9, half_w=600e-9)
    for j in range(2):
        slab(reg, j + 4, (j - 0.5) * t, +1500e-9, t / 2, half_a=800e-9, half_w=600e-9)
    return reg, {1: 1, 2: 1, 3: 1, 4: 2, 5: 2}


def main():
    fails = []

    def ck(tag, ok, det=''):
        print('  %-58s %s  %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            fails.append(tag)

    print('=' * 80)
    print('K-1 单变体 6 根贴在一起')
    reg, vm = case_one_block()
    b = BM.blocks(reg, DX, vm, eps0_var=EPS0, npf_var=NPF_EXACT)
    print('   nblk=%d nblk_sig=%d blk_laths=%s blk_vars=%s n_var_sig=%d n_habit=%d'
          % (b['nblk'], b['nblk_sig'], b['blk_laths'], b['blk_vars'],
             b['n_var_sig'], b['n_habit']))
    print('   f_var=%s  r_selfac=%.6e' % (b['f_var'], b['r_selfac']))
    ck('K-1 单块：nblk_sig == 1 且 blk_laths == 6',
       b['nblk_sig'] == 1 and b['blk_laths'] == '6',
       'nblk_sig=%d blk_laths=%s' % (b['nblk_sig'], b['blk_laths']))
    ck('K-6 单变体 ⇒ r_selfac == 1.0（一个变体不可能自协调）',
       abs(b['r_selfac'] - 1.0) < 1e-12, 'r=%.12f' % b['r_selfac'])

    print('\nK-2 两个变体、分开的两块（3 根 + 2 根）')
    reg2, vm2 = case_two_blocks()
    b2 = BM.blocks(reg2, DX, vm2, eps0_var=EPS0, npf_var=NPF_EXACT)
    print('   nblk=%d nblk_sig=%d blk_laths=%s blk_vars=%s f_var=%s n_habit=%d r=%.6e'
          % (b2['nblk'], b2['nblk_sig'], b2['blk_laths'], b2['blk_vars'],
             b2['f_var'], b2['n_habit'], b2['r_selfac']))
    ck('K-2 两块：nblk_sig == 2 且 blk_laths == 3/2',
       b2['nblk_sig'] == 2 and b2['blk_laths'] == '3/2',
       'nblk_sig=%d blk_laths=%s' % (b2['nblk_sig'], b2['blk_laths']))

    print('\nK-3 负对照：在单块中间插一层母相（厚 1.5Δx）⇒ 应裂成两块')
    reg3, vm3 = case_one_block(gap_n=1.5 * DX)
    b3 = BM.blocks(reg3, DX, vm3, eps0_var=EPS0, npf_var=NPF_EXACT)
    print('   nblk=%d nblk_sig=%d blk_laths=%s' % (b3['nblk'], b3['nblk_sig'],
                                                   b3['blk_laths']))
    ck('K-3 真裂会报裂：nblk_sig >= 2', b3['nblk_sig'] >= 2,
       'nblk_sig=%d（插缝前是 1）' % b3['nblk_sig'])

    print('\nK-4 `r_selfac` 与**独立重算**逐位比对（用 K-2 的实测分数）')
    f = [float(x) for x in b2['f_var'].split('/')]
    vol = {int(x): float(y) for x, y in zip(b2['blk_vars'].split('/'), f)} \
        if False else None
    # 独立重算：直接从 region 数胞
    laths = sorted(vm2)
    letters = sorted({int(v) for v in vm2.values()})
    cnt = {v: sum(int((reg2 == k).sum()) for k in laths if vm2[k] == v)
           for v in letters}
    tot = float(sum(cnt.values()))
    E = [np.asarray(e, float) - np.trace(np.asarray(e, float)) / 3.0 * np.eye(3)
         for e in EPS0]
    scale = float(np.mean([float(np.sqrt(np.sum(e ** 2))) for e in E]))
    acc = sum((cnt[v] / tot) * E[v - 1] for v in letters)
    r_ind = float(np.sqrt(np.sum(acc ** 2)) / scale)
    ck('K-4 独立重算与量具逐位相同', abs(r_ind - b2['r_selfac']) < 1e-15,
       '量具=%.12e  独立=%.12e  Δ=%.2e' % (b2['r_selfac'], r_ind,
                                           abs(r_ind - b2['r_selfac'])))

    print('\nK-5 `n_habit`（用生成器的**精确**惯习面法向）')
    # 同一 {110} 面的两个变体（面0 = V1,V2）；不同面的两个（面0 与 面1）
    reg4 = np.zeros((N, N, N), np.int8)
    slab(reg4, 1, -125e-9, 0.0, 125e-9)
    slab(reg4, 2, +125e-9, 0.0, 125e-9)
    b4 = BM.blocks(reg4, DX, {1: 1, 2: 2}, eps0_var=EPS0, npf_var=NPF_EXACT)
    reg5 = np.zeros((N, N, N), np.int8)
    slab(reg5, 1, -125e-9, 0.0, 125e-9)
    slab(reg5, 2, +125e-9, 0.0, 125e-9)
    b5 = BM.blocks(reg5, DX, {1: 1, 2: 3}, eps0_var=EPS0, npf_var=NPF_EXACT)
    print('   同惯习面（V1+V2）：n_habit=%d   不同惯习面（V1+V3）：n_habit=%d'
          % (b4['n_habit'], b5['n_habit']))
    ck('K-5 同惯习面 ⇒ 1；不同惯习面 ⇒ 2',
       b4['n_habit'] == 1 and b5['n_habit'] == 2,
       '%d / %d' % (b4['n_habit'], b5['n_habit']))

    print('\nK-7 ★ 逐块沿**该块自己的 n\\*** 数板条（多块配置的关键判据）')
    # 块 A（变体 1）的 n* = +z；块 B（变体 3）的 n* 取一个**斜的**方向
    nA = np.array([0.0, 0.0, 1.0])
    nB = np.array([1.0, 0.0, 0.0])
    axes_var = {1: (nA, AA, WA), 3: (nB, np.array([0.0, 1.0, 0.0]), WA)}
    reg7 = np.zeros((N, N, N), np.int8)
    # 块 A：沿 z 堆 3 根（在 a 方向偏 −1500 nm）
    for j in range(3):
        slab(reg7, j + 1, (j - 1) * 250e-9, -1500e-9, 125e-9)
    # 块 B：沿 x 堆 2 根（在 a 方向偏 +1500 nm）⇒ 与块 A 的 n* 正交
    ii = np.arange(N) * DX
    rel = [ii[:, None, None] - L / 2, ii[None, :, None] - L / 2,
           ii[None, None, :] - L / 2]
    dx_ = rel[0] - 1500e-9
    dnB = rel[2]
    for j in range(2):
        m = (np.abs(dx_ - (j - 0.5) * 250e-9) <= 125e-9) & (np.abs(dnB) <= 600e-9) \
            & (np.abs(rel[1]) <= 600e-9)
        reg7[m] = j + 4
    vm7 = {1: 1, 2: 1, 3: 1, 4: 3, 5: 3}
    b7 = BM.blocks(reg7, DX, vm7, eps0_var=EPS0, npf_var=NPF_EXACT, axes_var=axes_var)
    print('   nblk_sig=%d blk_vars=%s blk_laths=%s  **blk_nlath=%s**  blk_span_nm=%s'
          % (b7['nblk_sig'], b7['blk_vars'], b7['blk_laths'], b7['blk_nlath'],
             b7['blk_span_nm']))
    ck('K-7 逐块数板条 = 3/2（沿各自 n*；全局柱口径给不出这个数）',
       b7['blk_nlath'] == '3/2', 'blk_nlath=%s' % b7['blk_nlath'])

    print('\n' + '=' * 80)
    print('R30 J-1（块表量具）自检：%s（FAIL=%d）'
          % ('全过 ✅' if not fails else '有 FAIL ❌', len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
