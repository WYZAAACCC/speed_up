#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_closed.py —— **闭环配置**的启动器：由 `windowB_closure` 的闭式算出命令行。

为什么要有这个文件（而不是手写命令行）：
    用户在 R29 要求「把参数从规定值换成推导值」。手写命令行**看不出哪个数是推出来的**，
    也无法在参数被改动后自动更新。本文件让**每一个**闭环参数都带出处：
        n_lath ← C-2（α_KM 与 T_end）
        t, L, W ← Shuai 2026 / Wang 2026
        Δx     ← C-4 + 本仓库的 t/Δx ≥ 4
        q      ← C-3 的有序性上界 × ratio
        steps  ← C-3 的算力下界
        β_h    ← C-5 下界与 β_h(T) 取大
        overlap← 剂量–响应实测（1Δx）
        γ_F1   ← Murzinova 2017（`--gamma-murzinova` 时取带中值；默认仍是归档 0.15）

用法：
    python3 _bk_closed.py                     # 只打印推导与命令行（**不跑**）
    python3 _bk_closed.py --gamma 0.25 --tag cl1 --run
    python3 _bk_closed.py --steps-factor 0.5  # 只跑一半步数（预算不够时的降级，见记账）
"""
import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import windowB_closure as CL                                    # noqa: E402

PY = sys.executable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--N', type=int, default=96)
    ap.add_argument('--t-lath-nm', type=float, default=CL.T_LATH_MAIN_NM)
    ap.add_argument('--aspect', type=float, default=CL.ASPECT_LT_WANG)
    ap.add_argument('--alpha-km', type=float, default=CL.ALPHA_KM_REF)
    ap.add_argument('--T-end', type=float, default=298.0)
    ap.add_argument('--cool-ratio', type=float, default=0.8)
    ap.add_argument('--cool-rate', type=float, default=0.0,
                    help='0 = 用 C-3 的有序性上界 × cool-ratio')
    ap.add_argument('--gamma', type=float, default=0.15,
                    help='F1/F2 标量面能；0.15 = 归档值，0.25 = Murzinova 带中值')
    ap.add_argument('--beta-h', type=float, default=-1.0,
                    help='<0 = 用 C-5/β_h(T) 的较大者')
    ap.add_argument('--steps-factor', type=float, default=1.0,
                    help='<1 = 按比例缩短（**会使 C-3 有序性变差，必须记账**）')
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--arm', default='dry',
                    choices=['dry', 'wet', 'gpos', 'gneg', 'g0', 'auto', 'eng'],
                    help='`gpos` = F3 面能强制 100 J/m²（量具正对照：界面必须移动）。'
                         '★ 闭环算例若要判 V-6，**必须另跑一个与主臂步数配对的 gpos** ——'
                         '归档的 `gpos_L200` 只有 200 步、且 Δx 差 2 倍，拿它比会**假 FAIL**。')
    ap.add_argument('--nthreads', type=int, default=2)
    ap.add_argument('--tag', default='cl1')
    ap.add_argument('--out', default='_exp/_bk_closed')
    ap.add_argument('--every', type=int, default=100)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()

    rec = CL.recommend(N=a.N, t_lath_nm=a.t_lath_nm, aspect=a.aspect,
                       alpha_KM=a.alpha_km, T_f=a.T_end,
                       ratio_target=a.cool_ratio)
    print('=' * 100)
    print('windowB_closure.recommend() —— **闭环配置**（每个数都来自闭式，不是调出来的）')
    print('=' * 100)
    print('  C-2  n = floor(α_KM·(M_s − T_end)) = floor(%.4e × %.0f) = floor(%.3f) = **%d**'
          % (a.alpha_km, CL.M_S_TI64 - a.T_end, rec['n_lath_float'], rec['n_lath']))
    print('      第 k 根形核温度 T_k = M_s − k/α_KM: %s'
          % '  '.join('T%d=%.1f' % (k, CL.T_of_k(k, a.alpha_km))
                      for k in range(1, rec['n_lath'] + 1)))
    print('      ★ 时钟起点 = **T_1 = %.2f K**（不是 M_s=%.0f：n(M_s)=0，'
          't=0 预摆的那片就是第 1 根）' % (rec['T_start'], CL.M_S_TI64))
    print('  C-4  几何：t=%.0f nm（Shuai 2026）、L=%.0f nm（Wang 9:1）、W=%.0f nm'
          % (a.t_lath_nm, rec['L_lath'] * 1e9, rec['W_lath'] * 1e9))
    print('      Δx=%.0f nm ⇒ L_box=%.2f µm、t/Δx=%.2f、n_geo_cap=%d'
          % (rec['dx_nm'], rec['L_box_um'], rec['t_over_dx'], rec['n_geo_cap']))
    print('      Δx 候选逐个试的结果 (nm, t/Δx, n_cap): %s' % (rec['dx_tried'],))
    print('  C-3  有序性上界 q_cap=%.4e K/s；目标比 %.2f ⇒ **q=%.4e K/s**'
          % (rec['q_cap'], a.cool_ratio, rec['q']))
    print('      有序比 Δt_grow/Δt_nuc = %.3f（判据 ≤1）' % rec['ordered_ratio'])
    print('      步数下界=%.0f（与 MOB、q 无关）⇒ **steps=%d**'
          % (rec['steps_min'], rec['steps']))
    print('  C-5  β_h(T) 运行均值=%.2f；算力下界=%.2f ⇒ **β_h=%.2f**'
          % (rec['beta_h_T'], rec['beta_h_floor'], rec['beta_h_use']))
    print('  t_sim=%.4e s；r_nuc=%.1f nm；咬入=%.0f nm'
          % (rec['t_sim'], rec['r_nuc_nm'], rec['overlap_nm']))
    print('  recommend().ok = %s' % rec.get('ok'))

    steps = int(round(rec['steps'] * a.steps_factor))
    beta_h = (rec['beta_h_use'] if a.beta_h < 0 else a.beta_h)
    # ★★★ R29 修（`dry_cl1` 跑到 step 1000 时由 `_bk_thick.py` 抓到）：
    #   **播种厚度必须比物理板条厚多出"会被咬掉的那部分"。**
    #   共享界面（`attach`）把重叠区 `o` 从**两片各吃 o/2**：
    #     · 内部片（两张界面）共被吃 `o`      ⇒ 播种 `t_phys + o`
    #     · 端片（一张界面）被吃 `o/2`        ⇒ 播种 `t_phys + o/2`（末片走 `t_last_reduce`）
    #   不补的实测代价（`dry_cl1`：`--plate-T 510 --eng-t-nm 510 --nuc-overlap-nm 125`）：
    #     场 1（被咬两次）剔孤儿厚度 **391.8 nm** vs 物理靶 510 ⇒ **−23%**，
    #     掉出 V-8b 窗口 [408, 663]；场 2/3（还没被咬）503/508 ✓
    #   ⇒ 播种厚 = `t_phys + o`；`t_last_reduce = o/2` 把末片拨回去。
    #   ⚠ 同时必须把 `--plate-t-physical` 传下去：判据（V-8b / A-8）的靶是
    #     **物理厚**，不是播种厚 —— 否则"补对了"反而会被判 FAIL。
    t_seed_nm = a.t_lath_nm + rec['overlap_nm']
    print('  ★ 播种厚 = 物理厚 %.0f + 咬入 %.0f = **%.0f nm**'
          '（末片再减 %.0f nm）' % (a.t_lath_nm, rec['overlap_nm'], t_seed_nm,
                                    0.5 * rec['overlap_nm']))
    if a.steps_factor != 1.0:
        print('  ⚠⚠ --steps-factor=%.2f ⇒ steps=%d：**C-3 的有序性被破坏**，'
              '本次运行处于 burst regime，结论必须带这条记账' % (a.steps_factor, steps))
    if a.cool_rate > 0:
        print('  ⚠⚠ --cool-rate 由用户给定；ordered_ok=%s' % (CL.ordered_ok(
            a.cool_rate, 1e-9, a.alpha_km, rec['L_lath'])[0],))

    cmd = [PY, '-u', '_bk_exp.py',
           '--arm', a.arm,
           '--N', str(a.N), '--dx-nm', '%.4f' % rec['dx_nm'],           '--steps', str(steps),
           '--every', str(a.every), '--snap-every', '1000',
           '--pair-every', str(a.every),
           '--norm-smooth', '0', '--nthreads', str(a.nthreads),
           '--reinit-dt', '1e-4',
           '--grow-stack', '--nuc-every', '0',
           '--nuc-law', 'athermal',
           '--alpha-km', '%.6g' % a.alpha_km,
           '--cool-ratio', '%.4f' % a.cool_ratio,
           '--T-end', '%.2f' % a.T_end,
           '--gamma0', '%.4f' % a.gamma,
           '--plate-L', '%.2f' % (rec['L_lath'] * 1e9),
           '--plate-W', '%.2f' % (rec['W_lath'] * 1e9),
           '--plate-T', '%.2f' % t_seed_nm,
           '--plate-t-physical', '%.2f' % a.t_lath_nm,
           '--eng-r-nm', '%.3f' % rec['r_nuc_nm'],
           '--eng-t-nm', '%.2f' % t_seed_nm,
           '--eng-elong', '%.4f' % rec['elong'],
           '--eng-t-last-reduce-nm', '%.3f' % (0.5 * rec['overlap_nm']),
           '--nuc-overlap-nm', '%.3f' % rec['overlap_nm'],
           '--beta-h', '%.4f' % beta_h,
           '--eng-seed', str(a.seed),
           '--tag', a.tag, '--out', a.out]
    if a.cool_rate > 0:
        cmd += ['--cool-rate', '%.6g' % a.cool_rate]
    print('-' * 100)
    print('命令行（可直接复制）：')
    print('  cd %s' % _HERE)
    print('  ' + ' '.join(cmd))
    print('-' * 100)
    os.makedirs(os.path.join(_HERE, a.out), exist_ok=True)
    with open(os.path.join(_HERE, a.out, 'launch_%s.json' % a.tag), 'w',
              encoding='utf-8') as f:
        json.dump(dict(rec={k: (v if not isinstance(v, tuple) else list(v))
                            for k, v in rec.items()}, cmd=cmd, args=vars(a)),
                  f, ensure_ascii=False, indent=1)
    if not a.run:
        print('（未加 `--run` ⇒ 只打印，不执行）')
        return 0
    print('▶ 启动：tag=%s steps=%d dx=%.0f nm t=%.0f nm β_h=%.2f'
          % (a.tag, steps, rec['dx_nm'], a.t_lath_nm, beta_h))
    return subprocess.call(cmd, cwd=_HERE)


if __name__ == '__main__':
    raise SystemExit(main())
