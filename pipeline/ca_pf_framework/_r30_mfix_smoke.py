#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_mfix_smoke.py —— R30 P0-1 修复的**正/负对照**。

判据（预先写死，不得事后挪动）：
  P-1 **归档口径逐位不变**：`measure_state` 改后，`nslab_n`/`runs`/`nf3_col` 与
      "旧实现"（`r_col=300 nm`、`min_run=2`）**逐位相同**。
      ⚠ 这条是硬要求：改了它，全部历史读数就不可复现了。
  P-2 **新口径修好薄层**：层厚 2Δx 的 6 层堆叠，`nslab_n1` 必须 = 6（旧口径给 5）。
  P-3 **新口径在厚层上不倒退**：层厚 3.5Δx，`nslab_n1` 也必须 = 6。
  P-4 **可见性守卫有分辨力**：把某一层沿 a 方向挪出旧柱半径（300 nm）之外，
      该场的 `col_cover_<k>`（新口径）必须仍然 > 0.99，而**旧口径**下它应当显著 < 1。
  P-5 **真缺要报缺**（负对照）：真删掉一层 ⇒ `nslab_n1` 必须如实掉到 5。

跑法：  python3 _r30_mfix_smoke.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402

N, DX = 64, 62.5e-9
L = N * DX
N_HAB = np.array([0.0, 0.0, 1.0])
A_AX = np.array([1.0, 0.0, 0.0])
W_AX = np.cross(N_HAB, A_AX)
VMAP = {k: 1 for k in range(1, 7)}          # 6 场全同变体（= 一个块）


def stack(T_nm, shift_a_nm=0.0, drop_k=None, M=6, gap_nm=0.0):
    """沿 n* 堆 6 片；每片沿 a 长 2400 nm、沿 w 宽 1200 nm。"""
    reg = np.zeros((N, N, N), np.int8)
    T = T_nm * 1e-9
    gap = gap_nm * 1e-9
    c0 = np.array([L / 2, L / 2, L / 2])
    ii = np.arange(N) * DX
    for j in range(M):
        k = j + 1
        if drop_k is not None and k == drop_k:
            continue
        off = (j - (M - 1) / 2.0) * (T + gap)
        c = c0 + off * N_HAB
        if k == 2 and shift_a_nm:
            c = c + shift_a_nm * 1e-9 * A_AX
        rel = [ii[:, None, None] - c[0], ii[None, :, None] - c[1],
               ii[None, None, :] - c[2]]
        dn = N_HAB[0] * rel[0] + N_HAB[1] * rel[1] + N_HAB[2] * rel[2]
        da = A_AX[0] * rel[0] + A_AX[1] * rel[1] + A_AX[2] * rel[2]
        dw = W_AX[0] * rel[0] + W_AX[1] * rel[1] + W_AX[2] * rel[2]
        m = (np.abs(dn) <= T / 2) & (np.abs(da) <= 1200e-9) & (np.abs(dw) <= 600e-9)
        reg[m] = k
    return reg


def legacy(reg):
    """旧实现：`r_col=300 nm` + `min_run=2`（存档口径）。"""
    prof, runs = BM.column_profile(reg, DX, N_HAB, W_AX, A_AX, set(VMAP), 300e-9, 2)
    return len(runs), ','.join(str(x) for x in runs), BM._same_variant_adjacent(runs, VMAP)


def main():
    fails = []

    def ck(tag, ok, det=''):
        print('  %-62s %s  %s' % (tag, 'PASS' if ok else '**FAIL**', det))
        if not ok:
            fails.append(tag)

    for T_nm in (2 * 62.5, 3.5 * 62.5):
        reg = stack(T_nm)
        n0, r0, f0 = legacy(reg)
        m = BM.measure_state(reg, DX, N_HAB, W_AX, A_AX, VMAP)
        print('\n层厚 %.1f nm = %.2f Δx（6 片全在）' % (T_nm, T_nm / 62.5))
        print('   归档口径 nslab_n=%d runs=%s nf3_col=%d' % (n0, r0, f0))
        print('   测量输出 nslab_n=%d runs=%s nf3_col=%d' % (m['nslab_n'], m['runs'],
                                                             m['nf3_col']))
        print('   新口径   nslab_n1=%d runs1=%s nf3_col1=%d  r_col=%.0f nm'
              % (m['nslab_n1'], m['runs1'], m['nf3_col1'], m['r_col_nm']))
        print('   col_cover_min=%.4f' % m['col_cover_min'])
        ck('P-1 归档口径逐位不变（层厚 %.0f nm）' % T_nm,
           (m['nslab_n'], m['runs'], m['nf3_col']) == (n0, r0, f0),
           '%d/%s/%d' % (m['nslab_n'], m['runs'], m['nf3_col']))
        if abs(T_nm - 125.0) < 1:
            ck('P-2 新口径修好薄层：nslab_n1 == 6', m['nslab_n1'] == 6,
               '旧 %d → 新 %d' % (m['nslab_n'], m['nslab_n1']))
        else:
            ck('P-3 厚层不倒退：nslab_n1 == 6', m['nslab_n1'] == 6,
               'nslab_n1=%d' % m['nslab_n1'])

    # ---- P-4 可见性：把第 2 层沿 a 挪 1500 nm（远超旧柱半径 300 nm）----
    print('\nP-4 可见性守卫（第 2 层沿 a 挪 1500 nm；层厚 2Δx）')
    reg = stack(125.0, shift_a_nm=1500.0)
    m = BM.measure_state(reg, DX, N_HAB, W_AX, A_AX, VMAP)
    m_legacy = BM.measure_state(reg, DX, N_HAB, W_AX, A_AX, VMAP, r_col_auto=False)
    print('   旧柱(r=300nm, min_run=2)：nslab_n=%d runs=%s' % (m_legacy['nslab_n'],
                                                               m_legacy['runs']))
    print('   新柱(r=%.0f nm, min_run=1)：nslab_n1=%d runs1=%s'
          % (m['r_col_nm'], m['nslab_n1'], m['runs1']))
    print('   col_cover_2：旧口径 %.4f → 新口径 %.4f'
          % (m_legacy['col_cover_2'], m['col_cover_2']))
    ck('P-4 新口径仍看得见被挪开的层（cover_2 > 0.99）',
       m['col_cover_2'] > 0.99, 'cover_2=%.4f' % m['col_cover_2'])
    ck('P-4b 旧口径确实看不见它（cover_2 < 0.5）—— 说明守卫有分辨力',
       m_legacy['col_cover_2'] < 0.5, 'cover_2=%.4f' % m_legacy['col_cover_2'])

    # ---- P-5 真删一层 ⇒ 必须报缺 ----
    print('\nP-5 负对照：真删掉第 4 层（层厚 3.5Δx）')
    reg = stack(3.5 * 62.5, drop_k=4)
    m = BM.measure_state(reg, DX, N_HAB, W_AX, A_AX, VMAP)
    print('   nslab_n=%d nslab_n1=%d col_cover_min=%.4f'
          % (m['nslab_n'], m['nslab_n1'], m['col_cover_min']))
    ck('P-5 真缺报缺：nslab_n1 == 5', m['nslab_n1'] == 5, 'nslab_n1=%d' % m['nslab_n1'])

    print('\n' + '=' * 78)
    print('R30 P0-1 修复自检：%s（FAIL=%d）'
          % ('全过 ✅' if not fails else '有 FAIL ❌', len(fails)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
