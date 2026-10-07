#!/usr/bin/env python3
"""_r431_dgsign.py —— ★★★ **`Vt` 下降的定量归因**（`§190.7` 的候选解释 1/2/3 逐条判）

## 已知（`_r430` 实测，两臂同起点、只差冷速）
| 臂 | `dG_tip`（面中位数） | `Vt` |
|---|---|---|
| **abA**（守 C-3） | **全程负**（−1.0…−1.9e8） | 单调降（锯齿：每个新核也降） |
| **abB**（burst） | 由 −1.68e8 **穿过 0** 到 +3.3e7 | 由降转升（step≈200 起） |

## 本脚本要证的（**三条判据，缺一不可**）
**P-1 口径自证**：`dG_tip ≈ df + ed_tip`（逐行），其中 `df = ΔG_v(T)`。
    若这条不成立，说明我对三列的定义理解错了 ⇒ 后面两条作废。
**P-2 符号自证**：`sign(dG_face)` 必须能**预测** `sign(dVt/dstep)`。
    两臂、逐行核；有反例就报出来。
**P-3 定量**：解出"生长阈值" `ΔG_v(T*) = |ed_face|`，把 `T*` 换算成**步号**，
    与 abB 实测的穿越步号对比。

## 若三条都过 ⇒ 结论
**归档用常数 `df = DF = 3.5e8`；athermal 路径用 `ΔG_v(T)`，起点只有 1.23e8**
⇒ 起点净驱动力为负 ⇒ **新播的板条是亚临界的，只会溶解**。
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import windowB_closure as CL      # noqa: E402
import windowB_km as KM           # noqa: E402

BASE = '_exp/_bk_mb'
ARMS = [('dry_abA', 'A 守 C-3', 2.3524e6, 5922),
        ('dry_abB', 'B burst', 1.7412e7, 800)]
MS, T1 = 873.0, 849.0416666666666
DF_ARCHIVE = 3.5e8


def P(s):
    print(s, flush=True)


def f(r, k):
    v = r.get(k)
    if v in (None, ''):
        return float('nan')
    try:
        return float(v)
    except ValueError:
        return float('nan')


P('=' * 100)
P('_r431 —— `Vt` 下降的定量归因（判据 P-1/P-2/P-3）')
P('=' * 100)
P('\n[0] 对照量')
P('    T_start = T_1 = %.2f K ⇒ ΔG_v(T_1) = **%.4e J/m³**'
  % (T1, KM.drive_of_T(T1, KM.T0_TI64, CL.DS_REF)))
P('    室温 298 K      ⇒ ΔG_v(298) = **%.4e J/m³**'
  % KM.drive_of_T(298.0, KM.T0_TI64, CL.DS_REF))
P('    **归档用的常数** `df_const = DF = %.2e J/m³`（= ΔG_v(298)）'
  % DF_ARCHIVE)
P('    ⇒ 归档在**整段**冷却里都用室温那一档的驱动力；athermal 从 **1.23e8** 起步')
P('      ⇒ 两者在起点差 **%.2f 倍**' % (DF_ARCHIVE / KM.drive_of_T(T1, KM.T0_TI64, CL.DS_REF)))

all_ok1 = all_ok2 = True
pred = {}
for tag, desc, q, steps in ARMS:
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        P('\n[%s] ✗ 缺 series.csv' % tag)
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    P('\n' + '#' * 100)
    P('# %s（%s）  q=%.4e K/s  steps=%d  行数=%d' % (tag, desc, q, steps, len(rows)))
    P('#' * 100)

    # ---- 由 t_s 推 T，再算 df
    P('\n  %-6s %-8s %-9s %-11s %-11s %-11s %-11s %s'
      % ('step', 'T(K)', 'dG_tip', 'df=ΔG_v(T)', 'ed_tip', 'df+ed_tip',
         'dG_side', 'dVt/dstep'))
    prev = None
    bad1 = 0
    good2 = bad2 = 0
    for r in rows:
        ts = f(r, 't_s')
        T = T1 - q * ts if np.isfinite(ts) else float('nan')
        df = KM.drive_of_T(T, KM.T0_TI64, CL.DS_REF) if np.isfinite(T) else float('nan')
        dgt, edt = f(r, 'dG_tip'), f(r, 'ed_tip')
        dgs = f(r, 'dG_side')
        vt = f(r, 'Vt')
        dv = (vt - prev) if (prev is not None and np.isfinite(vt)) else float('nan')
        prev = vt if np.isfinite(vt) else prev
        # P-1：dG_tip ≈ df + ed_tip
        chk = df + edt
        rel = abs(dgt - chk) / max(abs(dgt), 1.0) if np.isfinite(dgt) else float('nan')
        if np.isfinite(rel) and rel > 0.15:
            bad1 += 1
        # P-2：sign(dG_face) 预测 sign(dVt)
        if np.isfinite(dgt) and np.isfinite(dv) and abs(dv) > 0:
            if (dgt > 0) == (dv > 0):
                good2 += 1
            else:
                bad2 += 1
        P('  %-6s %-8.1f %-9.3e %-11.3e %-11.3e %-11.3e %-11.3e %s'
          % (r.get('step'), T, dgt, df, edt, chk, dgs,
             ('%+.3e' % dv) if np.isfinite(dv) else '—'))
    P('\n  [P-1] `dG_tip` vs `df+ed_tip`：相对差 >15%% 的行数 = **%d/%d** ⇒ %s'
      % (bad1, len(rows), '✅ PASS' if bad1 == 0 else '⚠ 需复查口径'))
    P('  [P-2] `sign(dG_tip)` 预测 `sign(dVt)`：吻合 **%d**，反例 **%d** ⇒ %s'
      % (good2, bad2, '✅ PASS' if bad2 == 0 else
         '⚠ 反例 %d 条（注意 `dVt` 含**新核加入**的跳变，不是纯面运动）' % bad2))
    all_ok1 &= (bad1 == 0)

    # ---- P-3：生长阈值
    ed_med = np.nanmedian([abs(f(r, 'ed_tip')) for r in rows
                           if np.isfinite(f(r, 'ed_tip'))])
    P('\n  [P-3] |ed_tip| 中位 = **%.4e J/m³**' % ed_med)
    # 解 ΔG_v(T) = ed_med
    Tg = np.linspace(298.0, T1, 20000)
    dg = np.array([KM.drive_of_T(t, KM.T0_TI64, CL.DS_REF) for t in Tg])
    idx = np.where(dg >= ed_med)[0]
    if idx.size:
        Tstar = float(Tg[idx[0]])
        P('       ⇒ 生长阈值 **T\\* = %.1f K**（ΔG_v(T\\*) = |ed_tip|）' % Tstar)
        tstar = (T1 - Tstar) / q
        sstar = tstar / (f(rows[-1], 't_s') / max(int(rows[-1]['step']), 1))
        P('       ⇒ 到达 T\\* 需要 t = %.4e s ⇒ **约第 %.0f 步**（按末行平均 dt 折算）'
          % (tstar, sstar))
        pred[tag] = (Tstar, sstar)
    else:
        P('       ⇒ ⚠ 整个窗口内 ΔG_v 都 **达不到** |ed_tip| ⇒ **永远不生长**')
        pred[tag] = (float('nan'), float('inf'))
    vt = np.array([f(r, 'Vt') for r in rows])
    P('       实测 Vt：首 %.5f → 末 %.5f µm³（%+.1f%%）'
      % (vt[0] * 1e18, vt[-1] * 1e18, 100 * (vt[-1] / vt[0] - 1)))

P('\n' + '=' * 100)
P('[汇总]')
for tag, desc, q, steps in ARMS:
    if tag in pred:
        P('  %-8s %-10s 生长阈值 T\\* = %.1f K，约第 %.0f 步（预算 %d 步）'
          % (tag, desc, pred[tag][0], pred[tag][1], steps))
P('')
P('  ⇒ 若 T\\* 落在窗口内且步号 ≪ 预算 ⇒ A 臂**能**长起来，只是有很长的"溶解瞬态"；')
P('    若步号 ≳ 预算 ⇒ **A 臂在预算内长不起来**，路线 A 不可行。')
P('=' * 100)
