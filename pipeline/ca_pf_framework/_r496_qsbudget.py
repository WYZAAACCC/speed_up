#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r496_qsbudget.py —— 为**任务(5)**算账：准静态钟跑完全程要多少步、多少小时？

## 为什么要算

`_r492` 的集成冒烟（`N=64`、`nv=24`、`--nthreads 16`、700 步）实测：
* **qs 臂**：只完成 **1 档**（档 1 撞 `--qs-max-relax 400` 上限），第 2 档在进行中；
* 而 `T_end=298`、`ΔT=1/α_KM=23.958` ⇒ **全程 23 档**。

⇒ **按每档 400 步外推，全程要 ≈ 9200 步** ⇒ 这是任务(5) 的时间预算大项。

## 根因（`R477_QS_CLOCK.md §6.1` 已记）

`T > T* = 641.7 K` 的档位里**根本没有不动点**（场在持续溶解）
⇒ `Σ|ΔV|/V` 不衰减 ⇒ **每档都撞 400 步上限**。
而加了**超临界判据**之后，`T ≳ 378 K` 连核都放不下（`R479_SUPERCRIT.md §6`）
⇒ **前 ~19 档是纯等待**。

## 本脚本做什么

**只算账，不改任何东西**：
1. 从 `_r492` 的日志/CSV 读实测；
2. 按"每档 400 步"与"每档实测平均步数"两种口径外推全程；
3. 折算墙钟（用实测的 s/步）；
4. 给出**三条可选方案**及其代价，供拍板 —— **不自己决定**。
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402
import windowB_km as KM                                       # noqa: E402
from _r463_reinitcount import read_rows                        # noqa: E402

ROOT = '_exp/_bk_mb'


def log(p):
    if not os.path.exists(p):
        return ''
    with open(p, errors='replace') as fh:
        return fh.read()


def csv_ts(tag):
    rows = read_rows(os.path.join(ROOT, tag, 'series.csv'))
    if not rows:
        return None
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    out = {k: [] for k in ('step', 'wall_s', 't_s')}
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            for k in out:
                out[k].append(float(c[ix[k]]))
        except ValueError:
            continue
    return {k: np.array(v) for k, v in out.items()}


def main():
    print('=' * 88)
    print('R496  准静态钟跑完全程的步数/时间预算（为任务(5) 算账）')
    print('=' * 88)

    with open(os.path.join(ROOT, 'dry_r492on', 'meta.json')) as fh:
        ea = (json.load(fh).get('exp_args') or {})
    alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
    q = float(ea.get('cool_rate', 0.0))
    T_end = float(ea.get('T_end', 298.0))
    Ts_arg = float(ea.get('T_start', 0.0))
    T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))
    qs_dT = 1.0 / alpha
    n_stage = int(np.ceil((T_start - T_end) / qs_dT))

    lA = log('_w2_r492_r492on.log')
    stages = re.findall(r'\[qs\] 档 (\d+) 收敛：T=([\d.]+) K\s+用了 (\d+) 步', lA)
    steps_used = [int(s[2]) for s in stages]
    s = csv_ts('dry_r492on')
    sps = float('nan')
    if s is not None and len(s['wall_s']) > 1:
        sps = float(s['wall_s'][-1] - s['wall_s'][0]) / max(
            int(s['step'][-1] - s['step'][0]), 1)

    print('  配置（来自 `_r492` 的 meta）：α_KM=%.6g  q=%.4e K/s  T:%.1f→%.1f K'
          % (alpha, q, T_start, T_end))
    print('  ΔT = 1/α_KM = %.3f K  ⇒ **全程 %d 档**' % (qs_dT, n_stage))
    print('  实测：已完成档数 = **%d**，各档步数 = %s' % (len(stages), steps_used))
    print('  实测：**%.3f s/步**（N=64、nv=24、`--nthreads 16`）' % sps)
    print()

    # ---- 三种口径外推 ----
    cap = 400
    mean_used = float(np.mean(steps_used)) if steps_used else float('nan')
    print('  ── 全程步数外推（三种口径）──')
    print('   (a) 每档都撞上限 %d 步          ⇒ **%d 步**' % (cap, cap * n_stage))
    if steps_used:
        print('   (b) 按实测已完成档的均值 %.0f 步 ⇒ **%d 步**'
              % (mean_used, int(mean_used * n_stage)))
    print('   (c) 若"窗口内才算、窗口外不等待" ⇒ 见下面方案 B')
    print()
    print('  ── 折算墙钟（%.3f s/步）──' % sps)
    for nm, st in (('(a) 上限口径', cap * n_stage),
                   ('(b) 实测均值口径', int((mean_used if steps_used else cap) * n_stage))):
        print('   %-16s %6d 步 ⇒ **%.2f 小时**' % (nm, st, st * sps / 3600))
    print()

    # ---- 窗口在哪 ----
    ed = 2.087286e8
    lo, hi = 298.0, 1144.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(KM.drive_of_T(mid, KM.T0_TI64, KM.DS_REF)) > ed:
            lo = mid
        else:
            hi = mid
    T_growth = hi
    T_sc = 377.7          # `R479_SUPERCRIT.md §6` 实测的形核门槛
    print('  ── 两个门槛（决定"哪些档是纯等待"）──')
    print('   生长窗口  T* = **%.1f K**（`R470`，光滑椭球口径 2.09e8）' % T_growth)
    print('   形核门槛  T  = **%.1f K**（`R479`，带尖边圆盘口径 3.18e8）' % T_sc)
    n_wait = int(np.ceil((T_start - T_sc) / qs_dT))
    n_real = n_stage - n_wait
    print('   ⇒ `T > %.1f K` 的档 = **%d 档（纯等待）**；真正有效的 = **%d 档**'
          % (T_sc, n_wait, n_real))
    print()
    print('  ── 三条可选方案（**代价/收益，供拍板；本脚本不替你决定**）──')
    print('   方案 A｜照现在跑完 23 档：')
    print('      步数 ≈ %d（上限口径）⇒ **%.2f 小时**；物理上"完整走过冷却曲线"' % (
        cap * n_stage, cap * n_stage * sps / 3600))
    print('   方案 B｜钟**从 %d K 起步**（跳过 %d 个纯等待档）：'
          % (int(T_start - n_wait * qs_dT), n_wait))
    b_steps = cap * n_real
    T_B = T_start - n_wait * qs_dT
    # ★ 自查发现的错误 #94：第一版这里印的是"少算前 0 根核" —— **算错了**。
    #   正确算法：`n(T)` 是**状态函数** ⇒ 从 `T_start` 起步到 `T_B` 时，
    #   律**要求**的累计根数是 `n(T_B) = α_KM·(M_s − T_B)`；
    #   而按 A 方案一档一档走上来，第 1 档只要 `n(T_start)=1` 根
    #   ⇒ **差额 = n(T_B) − n(T_start)**，这就是"B 方案一上来就要放的根数"。
    n_at_A = float(CL.alpha_km_n_lath(T_start, alpha))
    n_at_B = float(CL.alpha_km_n_lath(T_B, alpha))
    print('      ⚠ **这不是"少算核"，而是"一上来就要放 %d 根"**（自查错误 #94）：'
          % int(round(n_at_B - n_at_A)))
    print('        `n(T)` 是**状态函数** ⇒ 走到 `T_B=%.1f K` 时律要求累计 **%.1f 根**；'
          % (T_B, n_at_B))
    print('        而 A 方案在 `T_start=%.1f K` 那档只要 **%.1f 根** ⇒ 差额 **%d 根**。'
          % (T_start, n_at_A, int(round(n_at_B - n_at_A))))
    print('        这 %d 根在 A 方案里本来也是**一档一档被要求**的，只是'
          % int(round(n_at_B - n_at_A)))
    print('        在 `T > %.0f K` 那 20 档里**全都会被超临界判据拒掉**。' % T_sc)
    print('      ⇒ **物理等价性成立的条件**：**超临界判据必须开着**。')
    print('        （不开的话，那些核会被放下去然后溶掉 ⇒ **路径就有影响了**。）')
    print('      步数 ≈ %d ⇒ **%.2f 小时**（省 **%.0f%%**）'
          % (b_steps, b_steps * sps / 3600,
             100 * (1 - b_steps / float(cap * n_stage))))
    print('   方案 C｜窗口外的档**不等待收敛**（只做固定几步就降 T）：')
    print('      步数 ≈ %d×小步数 + %d×%d ⇒ 介于 A/B 之间；'
          % (n_wait, n_real, cap))
    print('      ⚠ 需要改代码（新开关），且要证明"窗口外多等无益"。')
    print()
    print('=' * 88)
    print('★ 我的建议：**先做方案 B 的对照实验**（同一算例、只差钟的起点，'
          '预登记判据："末态几何在容差内一致"）')
    print('  —— 它同时验证了"跳过纯等待档是物理等价的"，又能把任务(5) 的用时压到 1/5。')
    print('=' * 88)
    return 0


if __name__ == '__main__':
    sys.exit(main())
