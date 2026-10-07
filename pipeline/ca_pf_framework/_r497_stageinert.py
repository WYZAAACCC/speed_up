#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r497_stageinert.py —— **早期的准静态档到底"惰性"吗？**（任务(5) 方案 B 的等价性取证）

## 为什么要先查这个（**不要先花 2.4 小时去跑 A/B**）

`R492_INTEG_AND_BUDGET.md §3.3` 我建议"方案 B：钟从 369 K 起步、跳过 20 个纯等待档"，
理由是"`n(T)` 是状态函数、那些核反正会被超临界判据拒掉"。

**但写完之后我意识到那个论证有一个洞**（**必须在花机时之前查清**）：

* 那 20 个档**不是真的什么都没干** —— **t=0 播下的那根初始板条在它们里面溶解**。
* 若真是这样，方案 B 跳掉它们之后，**初始板条会活到 370 K** ⇒
  **末态会多一根板条** ⇒ **不等价**。

## 本脚本只读**已归档**的数据（`dry_r492on`：qs 钟 + 超临界，跑到 step 700）

逐行读 `series.csv` 的 `vols`（各场体积，**斜杠分隔、单位 µm³**，教训 #55/#56），回答三问：

* **Q1** 档 1（T=849 K）里，**初始板条**（场 1）的体积怎么变？是溶、是长、还是不动？
* **Q2** 档 1 里**总转变体积**（`Vt`）与**场数**怎么变？
* **Q3** 有没有**除初始板条以外**的东西出现？（若有 ⇒ 超临界判据没拦住 ⇒ 我的前提也不对）

## 预登记判据（**先写死**）

| # | 检验 | 判据 |
|---|---|---|
| **Q1** | 初始板条在档 1 内的体积变化 | 报 `V(末)/V(起)`；**若 < 0.5 ⇒ 显著溶解** |
| **Q2** | 档 1 内 `nreg_used` 是否变化 | 变化 ⇒ 有事件发生 |
| **Q3** | 档 1 内**非场 1** 的体积和 | > 0 ⇒ 有别的东西 ⇒ 超出预期 |

**⇒ 判读**：
* 若 **Q1 显示显著溶解** ⇒ **方案 B 不等价（会多一根）** ⇒ 必须**同时**处理初始播种
  （例：B 方案下把初始播种挪到 370 K 再做，或接受"多一根"并记账）。
* 若 Q1 显示**基本不动** ⇒ 方案 B 的论证成立，可以做 A/B 对照（那时才值得花 2.4 h）。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL                                  # noqa: E402
import windowB_km as KM                                       # noqa: E402
from _r463_reinitcount import read_rows, n_nonzero_vols        # noqa: E402

ROOT = '_exp/_bk_mb'
TAG = 'dry_r492on'


def parse_vols(s):
    """`vols` 是**斜杠分隔**、单位 **µm³**。返回 float 列表（空/坏值给 nan）。"""
    out = []
    if not s:
        return out
    for x in s.split('/'):
        x = x.strip()
        if not x:
            continue
        try:
            out.append(float(x))
        except ValueError:
            out.append(np.nan)
    return out


def main():
    p = os.path.join(ROOT, TAG, 'series.csv')
    rows = read_rows(p)
    if not rows:
        print('✗ 读不到 %s' % p)
        return 2
    hdr = rows[0].split(',')
    ix = {h: i for i, h in enumerate(hdr)}
    need = ('step', 't_s', 'Vt', 'nreg_used', 'nslab_n', 'vols')
    miss = [k for k in need if k not in ix]
    if miss:
        print('✗ 缺列 %s' % miss)
        return 2

    recs = []
    for ln in rows[1:]:
        c = ln.split(',')
        if len(c) < len(hdr):
            continue
        try:
            r = dict(step=int(c[ix['step']]), t_s=float(c[ix['t_s']]),
                     Vt=float(c[ix['Vt']]), nreg=int(c[ix['nreg_used']]),
                     nslab=float(c[ix['nslab_n']]), vols=parse_vols(c[ix['vols']]))
        except ValueError:
            continue
        recs.append(r)

    with open(os.path.join(ROOT, TAG, 'meta.json')) as fh:
        ea = (json.load(fh).get('exp_args') or {})
    alpha = float(ea.get('alpha_km', CL.ALPHA_KM_REF))
    q = float(ea.get('cool_rate', 0.0))
    Ts_arg = float(ea.get('T_start', 0.0))
    T_start = Ts_arg if Ts_arg > 0 else float(CL.T_start_of_clock(alpha))

    print('=' * 92)
    print('R497  早期准静态档"惰性"取证（只读归档 %s）' % TAG)
    print('=' * 92)
    print('  α_KM=%.6g  q=%.4e K/s  T_start=%.2f K  ΔT=1/α=%.3f K  ⇒ 档边界温度：'
          % (alpha, q, T_start, 1.0 / alpha))
    print('     %s' % ', '.join('档%d@%.0fK' % (i + 1, T_start - i / alpha)
                                for i in range(4)))
    print('  归档行数 = %d（step %d→%d）' % (len(recs), recs[0]['step'], recs[-1]['step']))
    print()

    # 档 1 的结束温度 = T_start − ΔT ⇒ 用温度找档边界
    T1_end = T_start - 1.0 / alpha
    in1 = [r for r in recs if (T_start - q * r['t_s']) >= T1_end]
    print('  ── 档 1（T ≥ %.1f K）内的 %d 行 ──' % (T1_end, len(in1)))
    if len(in1) < 2:
        print('     ⚠ 行数不足，未取证')
        return 2
    print('     step    T(K)     Vt(m³)      nreg  nslab  场1体积(µm³)  非场1体积和')
    for r in in1[::max(len(in1) // 12, 1)]:
        T = T_start - q * r['t_s']
        v1 = r['vols'][0] if len(r['vols']) > 0 else float('nan')
        others = float(np.nansum(r['vols'][1:])) if len(r['vols']) > 1 else 0.0
        print('     %5d  %6.1f  %.4e  %4d  %4.0f  %12.4e  %12.4e'
              % (r['step'], T, r['Vt'], r['nreg'], r['nslab'], v1, others))

    v1_first = in1[0]['vols'][0] if in1[0]['vols'] else float('nan')
    v1_last = in1[-1]['vols'][0] if in1[-1]['vols'] else float('nan')
    ratio = (v1_last / v1_first) if (v1_first and np.isfinite(v1_first)
                                     and v1_first > 0) else float('nan')
    nreg_chg = in1[-1]['nreg'] - in1[0]['nreg']
    others_last = (float(np.nansum(in1[-1]['vols'][1:]))
                   if len(in1[-1]['vols']) > 1 else 0.0)

    print()
    print('  ── 判据 ──')
    print('  Q1 初始板条（场 1）体积：起 %.4e → 末 %.4e µm³ ⇒ 比值 **%.4f**'
          % (v1_first, v1_last, ratio))
    q1_dissolve = (ratio < 0.5) if np.isfinite(ratio) else None
    print('     ⇒ 判据（< 0.5 = 显著溶解）：%s'
          % ('**显著溶解**' if q1_dissolve else
             ('基本不动' if q1_dissolve is not None else '未取证')))
    print('  Q2 `nreg_used` 变化 = %+d ⇒ %s'
          % (nreg_chg, '有事件发生' if nreg_chg != 0 else '无事件'))
    print('  Q3 档 1 末"非场 1"体积和 = %.4e µm³ ⇒ %s'
          % (others_last, '有别的东西' if others_last > 1e-12 else '没有别的东西'))

    print()
    print('=' * 92)
    if q1_dissolve:
        print('★ 结论：**初始板条在档 1 里显著溶解** ⇒')
        print('  **方案 B（跳过这些档）不等价** —— 跳掉之后初始板条会活下来 ⇒ **末态多一根**。')
        print('  ⇒ 方案 B 若要做，**必须同时处理初始播种**（例：把 `t=0` 的播种挪到钟的起点再做），')
        print('     或者**接受"多一根"并显式记账**。**不得**直接把"跳过"当成等价。')
    elif q1_dissolve is False:
        print('★ 结论：初始板条在档 1 里**基本不动** ⇒ 方案 B 的论证成立 ⇒')
        print('  可以做 A/B 对照（那时才值得花 2.4 h）。')
    else:
        print('★ 未取证。')
    print('=' * 92)
    return 0


if __name__ == '__main__':
    sys.exit(main())
