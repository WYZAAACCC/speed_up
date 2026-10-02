#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_dxconsist.py --- ★ `norm_smooth=4` 的 **Δx 无关性**检验（R20 回归口径）

三个臂的真实配置（读各自 `meta.json`，**不猜**）
------------------------------------------------
| 目录 | Δx (nm) | `seed_scale` | 物理种子 L×W×T (nm) | 胞数 L×W×T |
|---|---|---|---|---|
| `mid250_ns4`     | 250 | 2 | 4000×1600×640 | 16.0×6.4×2.56 |
| `mid192_ns4`     | 125 | 1 | 2000× 800×320 | 16.0×6.4×2.56 |
| `mid192_s2_ns4`  | 125 | 2 | 4000×1600×640 | 32.0×12.8×5.12 |

⇒ **干净的单变量 Δx 对照是 `mid250_ns4` vs `mid192_s2_ns4`**：
物理初值完全相同，只有 Δx 减半（胞数相应加倍）。
`mid250_ns4` vs `mid192_ns4` 则**同时**改了 Δx 与物理种子尺寸 2× ⇒ **混淆**，
本脚本仍报出来但**明确标注为混淆臂**，不得单独用来下结论。

⚠ 本脚本第一版的两处问题（自查记录）
------------------------------------
1. 用的是**端点差** `(L[-1]-L[0])/dx` —— `R20` **明令禁止**（端点差有 ±1 胞噪声地板）。
   已改为**全样本最小二乘回归**。端点差口径曾给出 8.13 / 6.79，
   与回归口径的 8.70 / 10.2 明显不同。
2. 比较的是**混淆臂**（`mid250_ns4` vs `mid192_ns4`），
   且两臂用的**步数窗口不同**（一臂 452 步、一臂 184 步）
   ⇒ 若速率不是常数，窗口不同本身就制造差异。已改为**共同窗口**。
"""
import csv
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'^\s*\[\s*(\d+)\]\s')

ARMS = [
    ('mid250_ns4',    'A  Δx=250, 种子×2（16.0×6.4×2.56 胞；物理 4000×1600×640 nm）'),
    ('mid192_s2_ns4', 'C  Δx=125, 种子×2（**与 A 同一物理初值**）'),
    ('mid192_ns4',    'B  Δx=125, 种子×1（与 A 同胞数，物理尺寸减半 ⇒ 混淆臂）'),
]
I0 = 8          # 跳过前 8 行（初始瞬态 / 定标稳定）


def load(d):
    """返回 `(step_array, L_nm, W_nm, every_source)`。

    步轴来源优先级（**实测 > 猜**）：
      1. `series.csv` 的 `step` 列（修复后新算例有）；
      2. `log.txt` 里 `  [ NNN] …` 标记的**步号差分中位数**（实测 `every`）
         —— 见 `_r1_stepaxis.py` 的审计：`mid*` 一律 4、`e7*/e4/e5/e6` 一律 5，
         与各自启动命令行**逐条吻合**；
      3. `meta.json` 的 `every`（旧算例没有这个键）；
      4. 兜底 4，并**显式报警**。
    """
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    rows = list(csv.DictReader(open(p)))
    if not rows:
        return None
    every, src = None, ''
    lp = os.path.join(HERE, '_exp', d, 'log.txt')
    if os.path.exists(lp):
        marks = []
        for line in open(lp, errors='replace'):
            m = PAT.match(line)
            if m:
                marks.append(int(m.group(1)))
        if len(marks) > 2:
            dif = np.diff(np.array(marks, float))
            med = float(np.median(dif))
            if med >= 1 and np.all(dif == med):
                every, src = med, 'log 实测（标记间隔恒为 %g）' % med
            elif med >= 1:
                every, src = med, 'log 中位间隔 %g（**间隔不全等**，谨慎）' % med
    if not every:
        mp = os.path.join(HERE, '_exp', d, 'meta.json')
        if os.path.exists(mp):
            try:
                every = json.load(open(mp)).get('every')
                if every:
                    src = 'meta.every'
            except Exception:                                    # noqa: BLE001
                pass
    if not every:
        every, src = 4, '⚠ 兜底 4（log 与 meta 都取不到）'
    st = []
    for r in rows:
        try:
            v = float(r['step'])
            st.append(v if np.isfinite(v) else np.nan)
        except (ValueError, KeyError, TypeError):
            st.append(np.nan)
    st = np.array(st, float)
    if not np.isfinite(st).any():
        st = np.arange(len(rows), dtype=float) * float(every)
        src += ' ⇒ **用行号×every 重建**'
    L = np.array([float(r['L_cal']) * 1e9 for r in rows])
    W = np.array([float(r['W_cal']) * 1e9 for r in rows])
    # ★ G-2 剔除（台账 B-1c）：`ncomp > 1` ⇒ 目标变体分成多个连通分量
    #   ⇒ 那一步的 `max−min` 跨度**被碎片绑架**（`_r1_exp.py:42`），不得进入回归。
    good = np.ones(len(rows), bool)
    for i, r in enumerate(rows):
        v = r.get('ncomp')
        try:
            good[i] = (v is None or v == '' or float(v) == 1.0)
        except (TypeError, ValueError):
            good[i] = True
    return st, L, W, src, len(rows), good


def fit(t, y):
    A = np.vstack([t, np.ones_like(t)]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ sol
    dof = max(t.size - 2, 1)
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return float(sol[0]), float(np.sqrt(cov[0, 0])), float(resid @ resid)


print('=' * 100)
print('`norm_smooth=4` 的 Δx 无关性 —— **R20 全样本回归 + 共同窗口**')
print('=' * 100)

D = {}
for d, tag in ARMS:
    p = os.path.join(HERE, '_exp', d, 'series.csv')
    if not os.path.exists(p):
        print('%-46s ✗ 无 series.csv' % tag); continue
    o = load(d)
    if o is None:
        print('%-46s ✗ 空' % tag); continue
    st, L, W, src, n, good = o
    D[d] = (st, L, W, good)
    ng = int((~good).sum())
    print('%-46s rows=%-4d step=[%g…%g]%s'
          % (tag, n, np.nanmin(st), np.nanmax(st),
             ('  **剔除 G-2 污染 %d 步**' % ng) if ng else ''))
    print('%-46s 步轴来源：%s' % ('', src))

if len(D) < 2:
    print('\n⚠ 臂数 <2，无法比较。'); sys.exit(0)

# ★ 每个**对照**各用自己那两臂的重叠窗口（不取全局窗口）
#   理由：全局窗口被"最新、最短"的那一臂卡住（它还在跑），会无谓地损失统计功效。
#   正确做法是每一对比较用**那一对**的重叠区间 —— 窗口不同不影响"同窗口内比较"的合法性。


def fit_arm(d, lo, hi, quiet=False):
    """在 `[lo, hi]` 步窗口内对 `L_cal`/`W_cal` 做 `R20` 全样本回归（**剔除 G-2 污染步**）。"""
    st, L, W, good = D[d]
    m = np.isfinite(st) & np.isfinite(L) & np.isfinite(W) & good
    m &= (st >= lo) & (st <= hi)
    srt = np.sort(st[np.isfinite(st)])
    if srt.size > I0:
        m &= (st >= srt[I0])
    n = int(m.sum())
    if n < 8:
        if not quiet:
            print('   %-20s ✗ 窗口内点太少 (%d)' % (d, n))
        return None
    t = st[m]
    sL, eL, rssL = fit(t, L[m])
    sW, eW, _ = fit(t, W[m])
    sst = float(((L[m] - L[m].mean()) ** 2).sum())
    r2 = 1.0 - rssL / max(sst, 1e-300)
    r = sL / sW if sW > 0 else float('nan')
    sig = abs(r) * np.sqrt((eL / sL) ** 2 + (eW / sW) ** 2) if sL > 0 else float('nan')
    return dict(r=r, sig=sig, sL=sL, eL=eL, sW=sW, eW=eW, n=n, r2=r2,
                lo=float(t.min()), hi=float(t.max()))


def cmp2(a, b, clean):
    if a not in D or b not in D:
        print('\n  （%s vs %s：缺臂，跳过）' % (a, b)); return None
    lo = max(float(np.nanmin(D[a][0])), float(np.nanmin(D[b][0])))
    hi = min(float(np.nanmax(D[a][0])), float(np.nanmax(D[b][0])))
    print('\n  【%s】%s  vs  %s   窗口 step ∈ [%g, %g]'
          % ('干净单变量对照' if clean else '⚠ 混淆臂', a, b, lo, hi))
    if hi <= lo:
        print('     ✗ 无重叠窗口'); return None
    ra, rb = fit_arm(a, lo, hi, True), fit_arm(b, lo, hi, True)
    if ra is None or rb is None:
        print('     ✗ 窗口内数据不足'); return None
    for tag, z in ((a, ra), (b, rb)):
        print('     %-16s n=%-3d ΔL=%.4f±%.4f  ΔW=%.4f±%.4f  ΔL:ΔW=%.3f±%.3f  R²=%.4f'
              % (tag, z['n'], z['sL'], z['eL'], z['sW'], z['eW'], z['r'],
                 z['sig'], z['r2']))
    dd, ss = abs(ra['r'] - rb['r']), float(np.hypot(ra['sig'], rb['sig']))
    zz = dd / ss if ss > 0 else float('inf')
    print('     差 %.3f ± %.3f = **%.2f σ**  ⇒ %s'
          % (dd, ss, zz,
             '一致（<2σ）⇒ **Δx 无关性成立**' if zz < 2 else
             '不一致（≥2σ）⇒ **与 Δx 耦合**'))
    print('     ⚠ 检验功效：相对不确定度 %.1f%%（越小越有说服力）'
          % (100 * ss / max((ra['r'] + rb['r']) / 2, 1e-30)))
    return zz


print('\n' + '-' * 100)
z_clean = cmp2('mid250_ns4', 'mid192_s2_ns4', True)
print('\n混淆臂（Δx 与物理种子尺寸**同时**变）：')
z_conf = cmp2('mid250_ns4', 'mid192_ns4', False)
print('\n副产物（Δx 相同=125，物理种子 ×2）：')
cmp2('mid192_ns4', 'mid192_s2_ns4', False)

print('\n' + '=' * 100)
print('⚠ 记账：')
print('  1. 样本仍只有 **2 个 Δx**；要写成"Δx 收敛"仍需第三个点（如 Δx=62.5 nm）。')
print('  2. `_r1_exp.py` 曾把 `step`/`t_s`/`dG_max`/reinit 记账列写成空（已修，'
      '见 `_r1_csvfixchk.py` 的正/负对照）⇒')
print('     已有算例的步轴由 **`log.txt` 的标记间隔实测**得到（每个都是 4 或 5，'
      '与启动命令行吻合，见 `_r1_stepaxis.py`）。')
print('  3. 各对照用**各自**的重叠窗口；同一对照内两臂窗口相同 ⇒ 比较合法。')
print('  4. 若某臂仍在跑，结论是**临时的**，跑完后本脚本会给出更窄的不确定度。')
print('=' * 100)
