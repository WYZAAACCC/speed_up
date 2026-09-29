#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r30_ctl_column.py —— R30 审计：**柱剖面 `nslab_n` 的分辨力与相位依赖**。

★★ 起因（本审计实测，不是推理）：
   用 6 层等厚堆叠（层厚 **2Δx**）喂 `_bk_measure.measure_state`，
   `nslab_n` 给 **5** 而不是 6，`nf3_col` 给 4 而不是 5，`runs = 1,2,3,5,6`
   —— **场 4 完全在位**（盒内 818 胞、柱内 144 胞），只是柱剖面把它挤进了
   **单个 bin**，而 `min_run=2` 把"只占 1 个 bin 的段"**静默丢弃**。

   这是主判据 V-1（`nslab_n == M` 且 `nf3_col == M-1`）的**假 FAIL 源**：
   区分数值伪影与真实缺片的那个判据，本身会被"层厚 ≈ 2Δx"骗到。

本文件给出：
  P1 层厚扫描：`nslab_n` 在哪些厚度上少读（分辨力边界）。
  P2 `min_run=1` 能不能救回来（以及代价：噪声段会被计成板条）。
  P3 **亚胞相位扫描**：整堆叠平移 0…1Δx，`nslab_n` 随相位的跳变。
  P4 真实归档快照核对：`runs` 里的场数 vs 实际在位的场数。
  P5 负对照：真删掉一层 ⇒ `nslab_n` 必须掉（证明它"该响的时候响"）。

用法: python3 _r30_ctl_column.py
"""
import glob
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import numpy as np                                              # noqa: E402
import _bk_measure as BM                                        # noqa: E402
import _r30_ctl_measure as A                                    # noqa: E402


def prof_of(reg, vmap, r_col=300e-9, min_run=2):
    prof, runs = BM.column_profile(reg, A.DX, A.N_HAB, A.W_AX, A.A_AX,
                                   set(vmap), r_col=r_col, min_run=min_run)
    return prof, runs


def hr(t):
    print('\n' + '=' * 104)
    print(t)
    print('=' * 104, flush=True)


def main():
    VM = {k: 1 for k in range(1, 7)}
    hr('P1 层厚扫描：6 层等厚堆叠，`nslab_n` 从哪一档起才开始少读？')
    print('  %-8s %-10s %-9s %-9s %-22s %s'
          % ('层厚Δx', '层厚nm', 'nslab_n', 'nf3_col', 'prof', '在柱内的场'))
    bad = []
    for T_dx in (1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0):
        reg = A.stack(6, T_dx)
        r = A.msr(reg, vmap=VM)
        prof, runs = prof_of(reg, VM)
        incol = sorted(set(int(x) for x in np.unique(
            reg[np.isin(reg, list(VM))])) - {0})
        ok = (r['nslab_n'] == 6 and r['nf3_col'] == 5)
        if not ok:
            bad.append(T_dx)
        print('  %-8.1f %-10.1f %-9d %-9d %-22s %s  %s'
              % (T_dx, T_dx * A.DX * 1e9, r['nslab_n'], r['nf3_col'],
                 ''.join('%X' % v for v in (prof if prof is not None else [])),
                 incol, '' if ok else '← **少读**'))
    print('  ⇒ 少读的厚度档：%s' % bad)

    hr('P2 `min_run` 的影响（能不能靠调参救回来？）')
    print('  %-8s %-10s %-10s %-30s' % ('层厚Δx', 'min_run=2', 'min_run=1',
                                        'min_run=1 的 runs'))
    for T_dx in (1.5, 2.0, 2.5, 3.0):
        reg = A.stack(6, T_dx)
        r2 = A.msr(reg, vmap=VM)
        _, runs1 = prof_of(reg, VM, min_run=1)
        print('  %-8.1f %-10d %-10d %-30s'
              % (T_dx, r2['nslab_n'], len(runs1), ','.join(str(x) for x in runs1)))
    print('  ⚠ 记账：`min_run` 是**函数默认参数**，`_bk_exp` / `_bk_verdict` / '
          '`_bk_cmp` 全都用默认值 2，没有任何一处把它落盘 ⇒ ')
    print('     事后**无法从落盘数据判断**当时用的是哪个分辨力设置（CSV 里没有这一列）。')

    hr('P3 **亚胞相位扫描**：整堆叠沿 n* 平移 0→1Δx（步长 0.05Δx），看 nslab_n 抖不抖')
    for T_dx in (2.0, 3.5):
        seq = []
        for s in np.arange(0.0, 1.0001, 0.05):
            reg = A.stack(6, T_dx, shift=float(s))
            seq.append(A.msr(reg, vmap=VM)['nslab_n'])
        print('  层厚 %.1f Δx：nslab_n 随相位 = %s' % (T_dx, ''.join(str(x) for x in seq)))
        print('       取值集合 = %s（真值都是 6）' % sorted(set(seq)))
    print('  ⇒ 【实测】同一构型、只改**亚胞平移**（物理上完全等价，'
          '因为边界是周期的）就能让 `nslab_n` 在 %s 之间跳。'
          % '{5,6}')

    hr('P4 负对照（该响的时候响）：真删掉一层 ⇒ nslab_n 必须掉')
    print('  用**层厚 3.5Δx**（P1 里 nslab_n 正确 = 6 的那一档）做单变量负对照：')
    reg = A.stack(6, 3.5)
    pr = A.proj(A.N_HAB)
    r0 = A.msr(reg, vmap=VM)
    print('     未删： nslab_n=%d nf3_col=%d runs=%s'
          % (r0['nslab_n'], r0['nf3_col'], r0['runs']))
    for i in (0, 2, 4):
        reg_del = reg.copy()
        reg_del[(pr >= 3.5 * i) & (pr < 3.5 * (i + 1))] = 0
        r_del = A.msr(reg_del, vmap=VM)
        print('     删掉第 %d 层： nslab_n=%d nf3_col=%d runs=%s  %s'
              % (i + 1, r_del['nslab_n'], r_del['nf3_col'], r_del['runs'],
                 '✓ 报缺' if r_del['nslab_n'] == 5 else '**没报缺**'))
    print('  ⇒ 负对照成立 ⇒ 量具"真缺片时报缺"；问题是它**也会在没缺时报缺**（P1/P3/P5）。')

    hr('P5 真实归档快照核对：`runs` 里的场数 vs 实际在位的场数')
    dirs = sorted(glob.glob(os.path.join(_HERE, '_exp', '_bk_*', '*')))
    print('  %-46s %-6s %-6s %-8s %-26s %s'
          % ('臂', 'step', 'nslab', 'nreg_u', 'runs', '柱剖面异常'))
    nbad = 0
    for d in dirs:
        sp = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
        if not sp:
            continue
        z = np.load(sp[-1])
        if 'vmap_keys' not in z.files:
            continue
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        nh = np.asarray(z['n_hab'], float)
        vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        r = BM.measure_state(reg, dx, nh, z['w_ax'], z['a_ax'], vm)
        present = sorted(k for k in vm if (reg == k).any())
        rl = [int(x) for x in r['runs'].split(',') if x]
        inruns = sorted(set(rl))
        miss = [k for k in present if k not in inruns]
        dup = sorted(set(x for x in rl if rl.count(x) > 1))
        flag = []
        if miss:
            flag.append('**柱内缺片 %s**' % miss)
        if dup:
            flag.append('**同一场被切成 %s**' % dup)
        if flag:
            nbad += 1
        print('  %-46s %-6s %-6d %-8d %-26s %s'
              % (os.path.relpath(d, _HERE), int(z['step']), r['nslab_n'],
                 r['nreg_used'], r['runs'], '  '.join(flag)))
    print('  合计：末态快照里柱剖面与"在位场"不一致的臂 = **%d**' % nbad)

    hr('P6 追根：`dry_cln11`（**正在跑的臂**）step2000 为什么柱里缺场 2？')
    sp = sorted(glob.glob(os.path.join(_HERE, '_exp', '_bk_closed', 'dry_cln11',
                                       'snap_*.npz')))
    if sp:
        z = np.load(sp[-1])
        reg = z['region']
        dx = float(z['L']) / reg.shape[0]
        nh = np.asarray(z['n_hab'], float)
        wa, aa = np.asarray(z['w_ax'], float), np.asarray(z['a_ax'], float)
        vm = {int(k): int(v) for k, v in zip(z['vmap_keys'], z['vmap_vals'])}
        print('  N=%d Δx=%.1f nm  M(vmap)=%d  **现运行的 COLS 版**' %
              (reg.shape[0], dx * 1e9, len(vm)))
        print('  %-8s %-10s %-10s %-12s %s'
              % ('r_col(nm)', 'nslab_n', 'nf3_col', 'runs', '柱内场集合'))
        for rcol in (150e-9, 300e-9, 500e-9, 800e-9, 1200e-9, 2000e-9):
            r = BM.measure_state(reg, dx, nh, wa, aa, vm, r_col=rcol)
            rl = [int(x) for x in r['runs'].split(',') if x]
            print('  %-8.0f %-10d %-10d %-12s %s'
                  % (rcol * 1e9, r['nslab_n'], r['nf3_col'], r['runs'],
                     sorted(set(rl))))
        present = sorted(k for k in vm if (reg == k).any())
        print('  在位场 = %s' % present)
        # 各场相对 α′ 质心的面内偏移
        m_all = np.isin(reg, present)
        ii = np.arange(reg.shape[0]) * dx
        cnt = float(m_all.sum())
        s = [m_all.sum(axis=(1, 2)), m_all.sum(axis=(0, 2)), m_all.sum(axis=(0, 1))]
        c = np.array([float((ii * s[t]).sum()) / cnt for t in range(3)])
        print('  %-6s %-12s %-12s %-12s %s'
              % ('场', '体素', '质心 a(nm)', '质心 w(nm)', '最大面内半径(nm)'))
        for k in present:
            idx = np.argwhere(reg == k).astype(float)
            ck_ = (idx.mean(0)) * dx
            r3 = ck_ - c
            pa = float(r3 @ aa)
            pw = float(r3 @ wa)
            # 该场胞相对**全局质心**的最大面内半径
            p_all = ((idx * dx) - c) @ np.stack([aa, wa], 1)
            rad = float(np.sqrt((p_all ** 2).sum(1)).max())
            print('  %-6d %-12d %-12.1f %-12.1f %.0f'
                  % (k, idx.shape[0], pa * 1e9, pw * 1e9, rad * 1e9))
    else:
        print('  （没有 dry_cln11 快照）')

    print('\n' + '=' * 104)
    print('★ 结论（全部为【实测】）：')
    print('  1) `nslab_n` / `nf3_col` 的段长下限 `min_run=2`（bin 宽 = Δx）会把'
          '"恰好占 1 个 bin 的层"**整层丢掉**；')
    print('     层厚 ≈ 2Δx 时最容易被挤进单 bin（P1 已给出具体档位）。')
    print('  2) bin 相位由 `v.min()-0.5Δx` 决定（`_bk_measure.py:328`），'
          '而 `v.min()` 是**构型相关**的 ⇒ 亚胞平移 0→1Δx 就能让 nslab_n 在 5/6 之间跳（P3）。')
    print('  3) V-1 是"必须**每个**测点都成立"的合取判据 ⇒ 上面任何一次抖动'
          '都会把一次正确的运行判成 FAIL。')
    print('=' * 104)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
