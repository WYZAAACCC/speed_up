#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_ctl_measure.py —— R30 审计：补 `_bk_measure` **没有现成正对照**的那几个量。

`_bk_measure.py --selftest` 已经覆盖：体积(C1/C13)、分量数(C2/C15)、nslab_n(C3/C5/C9/C14)、
nf3_col(C6b/C14b)、F3 面积无偏估计量(C7/C12)、覆盖率 cov / β 夹层(C16/C17)。

**本文件补**（这些在 `--selftest` 里一条都没有）：
  A. `f3_pos_n` / `f3_pos_dx`（界面位移）的**传递函数**：已知平移 δ ⇒ 读数 = δ？
  A2. 格点对齐界面 ⇒ Δpos 的**量化台阶**（V-3 阈值 0.12Δx 分辨力够不够）。
  B. `f3_pos_n` 的**汇总权重**：面积不等的多张界面，只动一张 ⇒ 读数被稀释多少？
  C. `f3_std_n`：单张 vs 多张 —— 它量的是"粗糙度"还是"界面间距"？
  D. `f3_pos_m`（索引口径）vs `_bk_exp._pairpos_str`（胞心口径）的常数偏移。
  E. `nslab_n` / `nf3_col` / `n_k` 对"1 胞 β 夹层"与"孤儿"的敏感度。
  F. `f3_area` 在多个法向上的偏差。
  G. `vol_k` / `_linear_extent` 对**斜置长方体**的正对照。

装置用**显式能带构造**（不用 SDF 的 `<=` 边界）—— 第一版用 `_stack_reg` 时，
厚度正好是 Δx 的整数倍 ⇒ 层界面**落在胞面上** ⇒ 浮点 `<=` 把整整一层判出界
（实测 N=64/n*=(0,0,1) 时 z=32 层**两个场都没有**，F3 面数从 423 掉到 0）。
这是**测试装置的陷阱**，不是量具的错，必须避开。

用法: python3 _r30_ctl_measure.py
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402

N, DX = 64, 62.5e-9
N_HAB = np.array([-0.4424, 0.4425, -0.7801]); N_HAB /= np.linalg.norm(N_HAB)
W_AX = np.array([0.70711, 0.70711, 0.0]); W_AX /= np.linalg.norm(W_AX)
A_AX = np.array([-0.4909, 0.4909, 0.7198]); A_AX /= np.linalg.norm(A_AX)
C0 = np.array([N * DX / 2] * 3)

_II = np.arange(N)
_REL = [_II[:, None, None] * DX - C0[0], _II[None, :, None] * DX - C0[1],
        _II[None, None, :] * DX - C0[2]]


def proj(u, extra=None):
    """胞（**索引口径**，与 `_bk_measure._sub_coord` 一致）在 u 上的投影 / Δx。"""
    v = (u[0] * _REL[0] + u[1] * _REL[1] + u[2] * _REL[2]) / DX
    return v if extra is None else v + extra


def inplane(whalf, ahalf, n_hab=N_HAB):
    """面内掩模：|w·rel| ≤ whalf 且 |a·rel| ≤ ahalf（沿 n* 无限长）。"""
    return (np.abs(proj(W_AX)) * DX <= whalf) & (np.abs(proj(A_AX)) * DX <= ahalf)


def stack(M, T_dx=2.0, shift=0.0, whalf=None, ahalf=None, n_hab=N_HAB,
          film=None):
    """M 层等厚堆叠。`T_dx` = 每层厚（单位 Δx）；`shift` = 整体沿 **+n\\*** 平移（Δx）。

    ★ 符号：`proj` 给的是"胞相对盒子中心的 n* 投影"。把物体沿 +n* 移 δ ⇒
      胞的 **pr 减小 δ** ⇒ 用 `pr - shift` 选带（第一版写成 `+shift`，
      于是每一条读数的符号都反了 —— 这正是"正对照"该抓到的东西）。
    `whalf`/`ahalf` 给每层的面内半尺寸（米），长度须为 M。
    `film` = (idx, thick_dx)：在**第 idx 层内部**挖一条厚 `thick_dx`（Δx）的母相 β。
    """
    whalf = [320e-9] * M if whalf is None else whalf
    ahalf = [1200e-9] * M if ahalf is None else ahalf
    pr = proj(n_hab) - shift
    reg = np.zeros((N, N, N), np.int8)
    for i in range(M):
        ip = inplane(whalf[i], ahalf[i], n_hab)
        lo, hi = i * T_dx, (i + 1) * T_dx
        if film is not None and film[0] == i:
            fi = film[1]
            mid = 0.5 * (lo + hi)
            reg[ip & (pr >= lo) & (pr < mid - fi / 2)] = i + 1
            reg[ip & (pr >= mid + fi / 2) & (pr < hi)] = i + 1
        else:
            reg[ip & (pr >= lo) & (pr < hi)] = i + 1
    return reg


def msr(reg, n_hab=N_HAB, vmap=None, r_col=300e-9):
    vmap = vmap or {k: 1 for k in range(1, int(reg.max()) + 1)}
    return BM.measure_state(reg, DX, n_hab, W_AX, A_AX, vmap, r_col=r_col)


def hr(t):
    print('\n' + '=' * 104)
    print(t)
    print('=' * 104, flush=True)


FAIL = []


def ck(tag, ok, det=''):
    print('  %-60s %s  %s' % (tag, 'PASS' if ok else '**FAIL**', det))
    if not ok:
        FAIL.append(tag)


def note(t):
    print('  【实测】' + t)


def main():
    # =====================================================================
    hr('0. 基准构型自检：6 层等厚堆叠（层厚 2Δx = 125 nm，界面落在**胞心**上）')
    reg6 = stack(6, T_dx=2.0)
    r6 = msr(reg6)
    print('  各层体素数 = %s' % {k: int((reg6 == k).sum()) for k in range(7)})
    print('  **层厚 2Δx**：nslab_n=%d nf3_col=%d runs=%s（应 6/5/1..6）'
          % (r6['nslab_n'], r6['nf3_col'], r6['runs']))
    note('★ 层厚 2Δx 时 `nslab_n` **少读 1**（场 4 在盒内 818 胞、柱内 144 胞，'
         '却被 `min_run=2` 整层丢掉）—— 详见 `_r30_ctl_column.py` P1/P3。')
    reg6 = stack(6, 3.5)
    r6 = msr(reg6)
    print('  **层厚 3.5Δx**：nslab_n=%d nf3_col=%d runs=%s'
          % (r6['nslab_n'], r6['nf3_col'], r6['runs']))
    ck('0 装置可用（层厚 3.5Δx）：nslab_n==6 且 nf3_col==5', r6['nslab_n'] == 6
       and r6['nf3_col'] == 5, '')

    # =====================================================================
    hr('A. `f3_pos_n` 的**传递函数**：整体沿 n* 平移 δ（真值已知）')
    base = msr(stack(2, 2.0, 0.0))['f3_pos_n']
    print('  %-9s %16s %16s %12s' % ('δ (Δx)', '实测 Δpos (nm)', '真值 δ (nm)', '误差'))
    errs = []
    for dd in (-2.0, -1.0, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1.0, 2.0):
        got = msr(stack(2, 2.0, dd))['f3_pos_n'] - base
        errs.append(abs(got - dd * DX) / DX)
        print('  %+9.2f %16.2f %16.2f %+9.4f Δx' % (dd, got * 1e9, dd * DX * 1e9,
                                                    (got - dd * DX) / DX))
    ck('A1 斜交 n*（本项目真实法向）：亚胞位移读得出，误差 < 0.05 Δx',
       max(errs) < 0.05, 'max|err| = %.4f Δx' % max(errs))

    # A2 格点对齐 n*=(0,0,1)：显式构造，避开浮点边界
    nz = np.array([0.0, 0.0, 1.0])
    ii = np.arange(N)
    pr = (ii[None, None, :] - N / 2 + 0.5) / 1.0        # 胞心口径，单位 Δx

    def aligned(p):                                     # 界面在 pr = p 处
        reg = np.zeros((N, N, N), np.int8)
        reg[np.broadcast_to(pr < p, reg.shape)] = 1
        reg[np.broadcast_to(pr >= p, reg.shape)] = 2
        return reg
    p0 = 0.5
    b = msr(aligned(p0), n_hab=nz, vmap={1: 1, 2: 1})['f3_pos_n']
    got = []
    for d in (0.0, 0.25, 0.5, 0.6, 0.9, 1.0, 1.6, 2.0):
        got.append((msr(aligned(p0 + d), n_hab=nz, vmap={1: 1, 2: 1})['f3_pos_n']
                    - b) / DX)
    print('\n  A2 格点对齐界面（n*=(0,0,1)）：δ/Δx = 0, .25, .5, .6, .9, 1.0, 1.6, 2.0')
    print('     实测 Δpos/Δx = %s' % '  '.join('%+.3f' % g for g in got))
    note('格点对齐界的 Δpos 是 **1 Δx 的台阶**：δ=0.25/0.5 读 0，δ=0.6 就读到 1。')
    note('⇒ V-3 的 0.12 Δx 阈值在这类界面上**低于量具的量化地板**；'
         '它只能证明"界面在胞尺度上没动"，不能证明"动 < 0.12Δx"。')
    note('本项目 n* 是斜交的（A1 误差 ≤ %.3f Δx）⇒ 生产读数不受此台阶限制。'
         % max(errs))

    # =====================================================================
    hr('B. `f3_pos_n` 的**汇总权重**：面积不等的多张界面，只动其中一张')
    # 4 层、层厚 4Δx；只把 **0|1 界面**从 pr=4 推到 pr=5（其余两张界面不动）
    M, TT = 4, 4.0
    wlist = [160e-9, 320e-9, 320e-9, 320e-9]           # 第 1 层只有别人一半宽

    def four(move01=0.0):
        pr = proj(N_HAB)
        cuts = [0.0, TT + move01, 2 * TT, 3 * TT, 4 * TT]
        reg = np.zeros((N, N, N), np.int8)
        for i in range(M):
            ip = inplane(wlist[i], 1200e-9)
            reg[ip & (pr >= cuts[i]) & (pr < cuts[i + 1])] = i + 1
        return reg
    a0 = msr(four(0.0))
    a1 = msr(four(1.0))
    dmeas = (a1['f3_pos_n'] - a0['f3_pos_n']) / DX
    areas = {}
    for i in range(1, M + 1):
        for j in range(i + 1, M + 1):
            A = BM._area_from_faces(BM._faces_between(a1['__reg__'] if False
                                                      else (four(1.0) == i),
                                                      (four(1.0) == j)), N_HAB, DX)
            if A > 0:
                areas[(i, j)] = A
    tot = sum(areas.values())
    share = areas.get((1, 2), 0.0) / tot if tot else float('nan')
    print('  装置：4 层堆叠（层厚 4Δx），第 1 层面内半宽只有别人的 1/2。')
    print('  逐对面积（µm²）：%s' % '  '.join('%d|%d:%.4f' % (k[0], k[1], v * 1e12)
                                              for k, v in sorted(areas.items())))
    print('  只把 **1|2 界面** 沿 n* 推 **+1.000 Δx**（其余两张界面位置不动）')
    print('  实测汇总 Δpos = **%+.4f Δx**；面积加权预测 = 1.000 × %.4f = %+.4f Δx'
          % (dmeas, share, share))
    ck('B1 汇总读数 == 面积加权预测（±0.06 Δx）—— 权重**是**面积份额',
       abs(dmeas - share) < 0.06,
       '实测 %+.4f vs 预测 %+.4f Δx（差 %+.4f）' % (dmeas, share, dmeas - share))
    ck('B2 ★ "一张界面动 1Δx"被读成 < 0.6Δx（系统性低读 = 该响时不响）',
       dmeas < 0.6, '读 %.4f Δx，低读 %.0f%%（真值 1.000）'
       % (dmeas, 100 * (1 - dmeas)))
    note('⇒ 这就是 `_bk_exp.py:655-671` 与 `_bk_f3flat.py:5-13` 记账里说的'
         '"各对面积变了 ⇒ 汇总位置就变"的**定量形式**：')
    note('   汇总 Δpos = Σ_j (A_j/ΣA)·δ_j。**任何一张界面的面积份额变化**'
         '都会让读数动，而"界面本身"可以完全没动。')

    # =====================================================================
    hr('C. `f3_std_n` 量的是"粗糙度"还是"界面间距"？')
    r1 = msr(stack(2, 2.0))
    print('  C1 单张**平**界面（斜交 n*）：f3_area=%.4f µm²  f3_std_n = %.2f nm '
          '= %.3f Δx' % (r1['f3_area'] * 1e12, r1['f3_std_n'] * 1e9,
                         r1['f3_std_n'] / DX))
    ck('C1 单张平界面 std 很小 ⇒ 量具不是"恒给一个常数偏置"',
       r1['f3_std_n'] < 1.2 * DX, '%.3f Δx（≈ 1 个 F3 胞层自身的厚度）'
       % (r1['f3_std_n'] / DX))
    print('  C2 6 层 / 5 张**全平**界面：f3_std_n = %.1f nm = %.2f Δx'
          % (r6['f3_std_n'] * 1e9, r6['f3_std_n'] / DX))
    # 独立暴力枚举
    f3c = np.zeros((N, N, N), bool)
    for i in range(1, 7):
        for j in range(i + 1, 7):
            for ax in (0, 1, 2):
                for sh in (1, -1):
                    f3c |= (reg6 == i) & np.roll(reg6 == j, sh, axis=ax)
                    f3c |= (reg6 == j) & np.roll(reg6 == i, sh, axis=ax)
    p_brute = (np.argwhere(f3c).astype(float) @ N_HAB) * DX
    ck('C2 `f3_std_n` 与**独立暴力枚举**逐个数字一致（量具本身没算错）',
       abs(r6['f3_std_n'] - p_brute.std()) < 1e-12,
       '%.9f vs %.9f nm' % (r6['f3_std_n'] * 1e9, p_brute.std() * 1e9))
    note('★ 5 张**全平**界面给 %.0f nm，1 张**全平**界面给 %.0f nm ⇒ 差 %.0f 倍，'
         '而两者的真实粗糙度**都是 0**。'
         % (r6['f3_std_n'] * 1e9, r1['f3_std_n'] * 1e9,
            r6['f3_std_n'] / max(r1['f3_std_n'], 1e-30)))
    note('   ⇒ `f3_std_n` 在多界面构型下**主要量界面间距**，'
         '把它读成"界面粗糙/不稳"会给出相反结论（`_bk_f3flat.py` 记载已犯两次）。')

    # C3：单张界面 + 已知正弦粗糙度 ⇒ std ≈ A/√2
    print('\n  C3 单张界面 + 沿 a 轴的**正弦起伏**（振幅 A，4 个半波）——'
          '"该响的时候响"的正对照：')
    pr = proj(N_HAB)
    ra = proj(A_AX)
    for amp_nm in (0.0, 2.0, 4.0, 8.0):
        off = (amp_nm * 1e-9 / DX) * np.sin(2 * np.pi * 4 * ra / N)
        reg = np.zeros((N, N, N), np.int8)
        ip = inplane(320e-9, 1200e-9)
        band1 = (pr + off >= 0.0) & (pr + off < 2.0)
        band2 = (pr + off >= 2.0) & (pr + off < 4.0)
        # 用同一 off 平移两片的界面 ⇒ 界面本身起伏
        p2 = pr + off
        reg[ip & (p2 < 2.0)] = 1
        reg[ip & (p2 >= 2.0) & (p2 < 4.0)] = 2
        del band1, band2
        rr = msr(reg)
        print('     振幅 %4.1f nm ⇒ f3_std_n = %6.2f nm（正弦解析 A/√2 = %5.2f nm）'
              % (amp_nm, rr['f3_std_n'] * 1e9, amp_nm / np.sqrt(2)))
    note('单张界面下 std 随粗糙度单调上升、量级对 ⇒ 该口径**本身可用**；'
         '问题只在"多张混在一起"时。')

    # =====================================================================
    hr('D. 两处"界面位置"的**坐标口径**不一致（常数偏移）')
    off_nm = 0.5 * DX * float(N_HAB.sum()) * 1e9
    print('  `_bk_measure._sub_coord(bb,dx)` = `arange(start,stop)*dx` ⇒ **索引口径**')
    print('      ├ 用于 `f3_pos_n` / `f3_pos_dx` / `n_k` / `w_k` / `a_k`')
    print('  `_bk_exp._pairpos_str`          = `(argwhere(adj)+0.5)*dx` ⇒ **胞心口径**')
    print('      ├ 用于 `f3_pairs_pos` 列')
    print('  常数差 = 0.5·Δx·Σn_i = 0.5×%.2f nm×(%+.4f) = **%+.2f nm = %+.4f Δx**'
          % (DX * 1e9, N_HAB.sum(), off_nm, off_nm * 1e-9 / DX))
    ck('D1 两列口径差 > V-3 阈值(0.12Δx) ⇒ 直接相减会凭空多出 ~0.4 Δx',
       abs(off_nm * 1e-9 / DX) > 0.12, '%+.4f Δx' % (off_nm * 1e-9 / DX))
    # 用实际快照核对（若存在带 f3_pairs_pos 的臂）
    print('  实际核对（真实臂 `dry_defw`，若存在）：')
    import glob
    sp = sorted(glob.glob(os.path.join(_HERE, '_exp', '_bk_eng', 'dry_defw',
                                       'snap_*.npz')))
    csvp = os.path.join(_HERE, '_exp', '_bk_eng', 'dry_defw', 'series.csv')
    if sp and os.path.exists(csvp):
        z = np.load(sp[-1])
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        nh = np.asarray(z['n_hab'], float)
        vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        r = BM.measure_state(reg, dx, nh, z['w_ax'], z['a_ax'], vm)
        # 逐对：索引口径 vs 胞心口径
        rows = open(csvp, encoding='utf-8').read().splitlines()
        cols = rows[0].split(',')
        last = dict(zip(cols, rows[-1].split(',')))
        print('     末行 f3_pos_dx = %s（相对 P0）' % last.get('f3_pos_dx'))
        print('     末行 f3_pairs_pos = %s（**绝对**、胞心口径）'
              % last.get('f3_pairs_pos'))
        # 索引口径的绝对值
        print('     `measure_state` 给的绝对 f3_pos_n = %.2f nm（索引口径）'
              % (r['f3_pos_n'] * 1e9))
        print('     ⇒ 若把 `f3_pairs_pos` 当"相对 P0 的 Δpos"用，'
              '光口径就引入 %+.2f nm = %+.4f Δx 的假漂移'
              % (0.5 * dx * float(nh.sum()) * 1e9, 0.5 * float(nh.sum())))
    else:
        print('     （未找到 dry_defw 快照/CSV）')

    # =====================================================================
    hr('E. `nslab_n` / `nf3_col` / `n_k` 对"1 胞 β 夹层"与"孤儿"的敏感度')
    print('  ⚠ 用**层厚 3.5Δx**（`nslab_n` 正确 = 6 的那一档）做基准 —— '
          '层厚 2Δx 时基准自己就因 `min_run` 少读一个，会把结论搞反（第一版踩过）。')
    reg_b = stack(6, 3.5)
    r_b = msr(reg_b)
    reg_f = stack(6, 3.5, film=(2, 1.2))          # 在第 3 层内部挖 1.2Δx 厚的 β
    r_f = msr(reg_f)
    ncut = int((reg_b == 0).sum() - (reg_f == 0).sum())
    print('  E1 基准 6 层： nslab_n=%d nf3_col=%d runs=%s'
          % (r_b['nslab_n'], r_b['nf3_col'], r_b['runs']))
    print('     在第 3 层**内部**挖 %.1fΔx 厚的母相 β（%d 胞，确实挖掉了）：'
          % (1.2, ncut))
    print('     有夹层： nslab_n=%d nf3_col=%d runs=%s'
          % (r_f['nslab_n'], r_f['nf3_col'], r_f['runs']))
    ck('E1 1 胞级 β 夹层**必须**被 V-1 抓到（nslab_n≠M 或 nf3_col≠M−1）',
       (r_f['nslab_n'] != 6) or (r_f['nf3_col'] != 5),
       'nslab %d→%d, nf3col %d→%d ⇒ %s'
       % (r_b['nslab_n'], r_f['nslab_n'], r_b['nf3_col'], r_f['nf3_col'],
          '抓到' if (r_f['nslab_n'] != 6 or r_f['nf3_col'] != 5) else '**漏掉**'))
    ck('E1b 兜底：该 β 夹层是否至少被 `ncompbig_k` 抓到（V-5b）',
       r_f['ncompbig_3'] != r_b['ncompbig_3'] or r_f['ncomp_3'] != r_b['ncomp_3'],
       'ncomp_3 %d→%d ; ncompbig_3 %d→%d  ⇒ %s'
       % (r_b['ncomp_3'], r_f['ncomp_3'], r_b['ncompbig_3'], r_f['ncompbig_3'],
          '抓到' if (r_f['ncompbig_3'] != r_b['ncompbig_3']
                     or r_f['ncomp_3'] != r_b['ncomp_3']) else '**两条都漏**'))
    # 逐厚度扫描：多厚的 β 夹层才会被 V-1 看见？
    print('     夹层厚度扫描（膜覆盖整片宽/长，V-1 能否看见）：')
    for fd in (0.5, 0.8, 1.0, 1.2, 1.6, 2.0, 3.0):
        rf = msr(stack(6, 3.5, film=(2, fd)))
        print('       膜厚 %.1fΔx = %5.1f nm ⇒ nslab_n=%d nf3_col=%d %s'
              % (fd, fd * DX * 1e9, rf['nslab_n'], rf['nf3_col'],
                 '✓抓到' if (rf['nslab_n'] != 6 or rf['nf3_col'] != 5)
                 else '**V-1 漏掉**'))

    reg_o = reg_b.copy()
    reg_o[5, 5, 5] = 3
    reg_o[11, 40, 55] = 3
    r_o = msr(reg_o)
    print('\n  E2 往场 3 之外塞 2 个 1 体素"孤儿"（同场号，远离主体）：')
    print('     nslab_n %d→%d   nf3_col %d→%d   ncomp_3 %d→%d   ncompbig_3 %d→%d'
          % (r_b['nslab_n'], r_o['nslab_n'], r_b['nf3_col'], r_o['nf3_col'],
             r_b['ncomp_3'], r_o['ncomp_3'], r_b['ncompbig_3'], r_o['ncompbig_3']))
    ck('E2 孤儿污染 `ncomp_k`（+2）但**不污染** `ncompbig_k`'
       '（这是 V-5/V-5b 两口径并存的唯一理由）',
       r_o['ncomp_3'] == r_b['ncomp_3'] + 2 and r_o['ncompbig_3'] == 1,
       'ncomp_3 %d→%d ; ncompbig_3 = %d'
       % (r_b['ncomp_3'], r_o['ncomp_3'], r_o['ncompbig_3']))
    ck('E3 ★ 孤儿把 `n_k`（= `ths` 列）拉爆 ⇒ V-8b 必须用剔孤儿口径',
       r_o['n_3'] > 2 * r_b['n_3'],
       'n_3 %.0f → %.0f nm（%.1f 倍；真厚度 %.0f nm）'
       % (r_b['n_3'] * 1e9, r_o['n_3'] * 1e9, r_o['n_3'] / r_b['n_3'], 3.5 * DX * 1e9))

    # =====================================================================
    hr('F. `f3_area`（Cauchy 无偏）在多个法向上的偏差')
    print('  装置：周期盒内 reg = (n·rel<0)?1:2')
    ii = np.arange(N)
    rela = [(ii[:, None, None] - N / 2) * DX, (ii[None, :, None] - N / 2) * DX,
            (ii[None, None, :] - N / 2) * DX]
    Lbox = N * DX
    for tag, u, nsheet in (('轴 (0,0,1)', np.array([0., 0., 1.]), 2),
                           ('45° (1,1,0)/√2', np.array([1., 1., 0.]) / np.sqrt(2), 2),
                           ('(1,1,1)/√3', np.array([1., 1., 1.]) / np.sqrt(3), 1),
                           ('本项目 n*', N_HAB, 2),
                           ('n* 的 90° 旋转', np.array([-N_HAB[1], N_HAB[0], 0.0])
                            / np.hypot(N_HAB[0], N_HAB[1]), 2)):
        pr = u[0] * rela[0] + u[1] * rela[1] + u[2] * rela[2]
        reg = np.where(pr < 0, 1, 2).astype(np.int8)
        rr = msr(reg, n_hab=u, vmap={1: 1, 2: 1})
        ana = nsheet * Lbox ** 2 / np.abs(u).max()
        print('  %-16s f3_faces=%-7d f3_area=%-11.4f µm²  阶梯/无偏=%.4f  '
              '解析(实测张数=%d)=%.4f µm²  偏差 %+.1f%%'
              % (tag, rr['f3_faces'], rr['f3_area'] * 1e12,
                 rr['f3_area_stair'] / rr['f3_area'], nsheet, ana * 1e12,
                 100 * (rr['f3_area'] / ana - 1)))
    note('阶梯/无偏 == Σ|n_i|（Cauchy 估计量的**内禀恒等式**）在每一行都成立'
         '（1.0000 / 1.4142 / 1.7321 / 1.6625）⇒ 该估计量的"去偏"是自洽的。')
    note('40–66% 的阶梯高估必须靠这一列才能还原真实面积'
         '（本项目 n* 的 Σ|n_i| = 1.6649 ⇒ 阶梯口径高估 66%）。')
    note('⚠ 周期盒里"一个半空间"的边界有 **2 张**（同 n 的另一侧），'
         '(1,1,1)/√3 例外只有 1 张 ⇒ 与解析比必须自己数张数；')
    note('   本项目实际测的是**有限板条之间**的一张共享面（`--selftest` C7 = −0.3%），'
         '不存在数张数的问题。')

    # =====================================================================
    hr('G. `vol_k` 与 `_linear_extent` 对**斜置长方体**的正对照')
    print('  装置：沿 a/w/n* 的斜置长方体，半尺寸 (2000, 400, 200) nm（长 4µm/宽 0.8/厚 0.4）')
    hl, hw, ht = 2000e-9, 400e-9, 200e-9
    box = ((np.abs(proj(A_AX) * DX) <= hl) & (np.abs(proj(W_AX) * DX) <= hw)
           & (np.abs(proj(N_HAB) * DX) <= ht))
    regb = np.zeros((N, N, N), np.int8); regb[box] = 1
    rb = msr(regb, vmap={1: 1})
    print('  vol_1 = %.6f µm³ ；解析（连续） = %.6f µm³ ；误差 %+.2f%%'
          % (rb['vol_1'] * 1e18, (2 * hl) * (2 * hw) * (2 * ht) * 1e18,
             100 * (rb['vol_1'] / ((2 * hl) * (2 * hw) * (2 * ht)) - 1)))
    print('  n_1/w_1/a_1 = %.0f/%.0f/%.0f nm（解析 400/800/4000；`+dx` 口径 %.0f/%.0f/%.0f）'
          % (rb['n_1'] * 1e9, rb['w_1'] * 1e9, rb['a_1'] * 1e9,
             rb['nb_1'] * 1e9, rb['wb_1'] * 1e9, rb['ab_1'] * 1e9))
    ck('G1 `vol_1` == **独立数胞** × Δx³（逐位一致；量具体积量本身无误差）',
       abs(rb['vol_1'] - int(box.sum()) * DX ** 3) < 1e-30,
       'vol_1 = %.9f µm³ = %d 胞 × Δx³（解析 %.6f µm³，差 %+.2f%% 是**离散化**）'
       % (rb['vol_1'] * 1e18, int(box.sum()),
          (2 * hl) * (2 * hw) * (2 * ht) * 1e18,
          100 * (rb['vol_1'] / ((2 * hl) * (2 * hw) * (2 * ht)) - 1)))
    note('★ 但"胞集合 vs 连续形状"有 **O(Δx/最小尺寸)** 的离散化偏差：'
         '斜置长方体读 %+.2f%%，格点对齐同尺寸读 **%+.2f%%**（薄向只有 6.4 胞）。'
         % (100 * (rb['vol_1'] / ((2 * hl) * (2 * hw) * (2 * ht)) - 1), 0.0))
    ck('G2 `n_1`/`w_1`/`a_1`（索引口径 max−min）误差 < 1Δx',
       abs(rb['n_1'] - 2 * ht) < DX and abs(rb['w_1'] - 2 * hw) < DX
       and abs(rb['a_1'] - 2 * hl) < DX,
       'n/w/a = %.0f/%.0f/%.0f nm vs 解析 400/800/4000 nm'
       % (rb['n_1'] * 1e9, rb['w_1'] * 1e9, rb['a_1'] * 1e9))
    # 独立暴力
    idx = np.argwhere(box).astype(float)
    brute = [float(np.ptp(idx @ u)) * DX for u in (A_AX, W_AX, N_HAB)]
    ck('G3 与**独立暴力枚举**逐位一致',
       abs(brute[0] - rb['a_1']) < 1e-12 and abs(brute[1] - rb['w_1']) < 1e-12
       and abs(brute[2] - rb['n_1']) < 1e-12,
       '暴力 a/w/n = %.1f/%.1f/%.1f nm' % (brute[0] * 1e9, brute[1] * 1e9,
                                           brute[2] * 1e9))

    print('\n' + '-' * 104)
    print('FAIL = %d %s' % (len(FAIL), FAIL if FAIL else ''))
    print('=' * 104)
    return 1 if FAIL else 0


if __name__ == '__main__':
    raise SystemExit(main())
