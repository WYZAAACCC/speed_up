#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R461 —— **SDF 健康度**量具（为任务(1) 的 S2/reinit 判定取证）。

## 为什么要这个量具

`NEXT_TASKS_FOR_REVIEW.md` §五 S2 的**初判**是：

    「`reinit` 形同虚设：`reinit_dt=1e-4` 而 `dt≈2.7e-8` ⇒ 3733 步才触发一次」
    ⇒ **后果是 φ 不再是距离函数 ⇒ 界面速度失真**

**这句话的后半截（"后果"）从来没有被直接量过。** 本量具就是去量它：
**跑完之后 φ 到底还是不是距离函数？**

⚠ 在量之前必须先解决 `R1_REINIT_AUDIT.md` 留下的**未决问题**（该文件 §1.6 与 §5.9）：

    带内 `median|∇d2|` 系统性 < 1（0.76–0.92），这**是不是"差分场本来就该如此"**？
    （薄板 t = 3.2 胞 ⇒ ±6 胞的带把整个板厚都包进来，
      板的中轴面上真实距离函数的 `|∇d|` 可以 < 1）
    还是**真的斜率退化**？ —— 该审计**无法用现有读数判定**，
    并明确写了「**在判定之前，不得据 `med@6dx` 做任何参数决策**」。

⇒ 本量具的设计就是为了**一次判开**：对**同一个场**同时报 4 个带宽
（`1.5 / 3 / 6 / 12` 胞），并且**在解析已知答案上先跑一遍同样的读数**（见下）。

## 预登记的自检（**先写死、必须能失败**）

用户硬要求：「凡'最小化/最优化'得到的量，必须先用**解析已知答案**验证最小化器本身，
且**正对照必须预先写死、必须能失败**」。本量具的核心运算不是最小化器，
但同样有一条**解析已知答案**：**精确 SDF 的 `|∇φ| ≡ 1`**。

| # | 场 | 解析真值 | 类型 | 预登记的判据 |
|---|---|---|---|---|
| **T1** | 平面 `φ = x − x0` | `med|∇φ| = 1` | 正对照 | `|med − 1| ≤ 1e-3` |
| **T2** | 球 `φ = r − R`（R = 12Δx） | `med|∇φ| = 1` | 正对照 | `|med − 1| ≤ 5e-3` |
| **T3** | 抛物 `φ = (x−x0)²/(2L)` | `med|∇φ| ≈ 0.39` | **负对照** | **必须 `|med − 1| > 0.3`**（即**必须报 FAIL**） |
| **T4** | **平台场** `clip(x−x0, ±3Δx)`（板内 `φ ≡ −sdf` 的退化形态） | 带内 90.6% 平坦 ⇒ `med = 0` | **负对照** | **必须 `med ≤ 0.10` 且 `frac_flat > 0.5`**（见下方"T4 预登记更正"） |
| **T5** | `clip(x−x0, ±20Δx)`（**远场截断、但 6Δx 带内未被截**） | 带内 `|∇φ| ≡ 1` | **正对照** | `|med − 1| ≤ 1e-3` **且 `frac_flat ≤ 0.01`** |

### ⚠ T4 预登记更正（**第一版写错了，此处留痕**）

第一版把 T4 的判据写成 `med ∈ [0.35, 0.65]`，理由是"带内一半 1、一半 0"。**实测 `med = 0.000000`、`frac_flat = 0.906` ⇒ 判 FAIL。**
**这个 FAIL 是我的预登记算错了，不是量具错了**：
`clip(x−x0, ±3Δx)` 的值域是 `[−3Δx, +3Δx]`，而带是 `|φ| ≤ 6Δx`
⇒ **整个域都落在带内** ⇒ 带内 = 全域，其中平坦部分占 `1 − 6/64 = 90.6%` ⇒ `med = 0`。
即**量具的行为完全正确**（它把一个严重退化的场报成了严重退化），
错的是"一半一半"这个心算（它假设带只覆盖界面附近的壳，对**有界场**不成立）。

⇒ 按纪律：**不为了让它过而放宽阈值**，而是**改推导**：T4 要检验的命题是
「量具能把平台场报成坏场」，正确登记形式是 `med` 远离 1（取 `≤0.10`）**且** `frac_flat` 大（`>0.5`）。
**T4 的 FAIL 记录保留在上面（第一版输出），不得抹掉。**

### ⚠ T5 为什么必须加（它是 T4 暴露出来的那个混淆的隔离器）

T4 的更正暴露一件事：**"`med@6Δx` 偏低"有两个完全不同的来源** ——
①**场真的退化了**；②**带太宽，把"值域被截断的远场"包了进来**。
R1 审计 §1.6 的未决问题（`med@1.5dx = 0.76–0.92 < med@6dx`）正是在问这两者。
**T5 就是把②单独造出来**：远场被截断（值域有界），但 6Δx 带**完全落在未截断区**
⇒ 若量具在 T5 上给 1.000，则"带太宽"**只在场本身的值域 < 带时**才会污染读数
⇒ 那时正确做法是**缩带**（用 `|d2| ≤ 1.5Δx` 那一列），而不是宣布场退化。

**T3/T4 若"通过"（即量具报它们健康），本量具整体判定为不可信并中止。**

## 输出

对每个快照报一张表：`band_cells × {单场 med |∇φ_k|}` 与 `× {配对 med |∇d2|}`，
并把读数按 `step` 写成 JSONL，便于看**退化随时间**的趋势。

用法：
    python3 _r461_sdfhealth.py --selftest                       # 只跑自检
    python3 _r461_sdfhealth.py --npz <快照> [--npz ...]         # 量指定快照
    python3 _r461_sdfhealth.py --tag dry_abB                    # 量该臂**全部**快照
    python3 _r461_sdfhealth.py --tag dry_abB --last 3           # 只量最后 3 帧
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

import numpy as np

BANDS = (1.5, 3.0, 6.0, 12.0)          # 胞；覆盖 R1 审计 §1.6 的三档 + 更宽一档
# ★ 预登记的判据（写死在这里，不在运行时算）
TOL_PLANE = 1e-3
TOL_SPHERE = 5e-3
T3_MIN_BAD = 0.3                        # T3 的 med 必须离 1 至少这么远
T4_MED_MAX = 0.10                       # T4（平台场）的 med 必须 ≤ 这个值
T4_FRAC_FLAT_MIN = 0.5
T5_TOL = 1e-3                           # T5（远场截断但带内未截）必须仍给 1
T5_FRAC_FLAT_MAX = 0.01


# ---------------------------------------------------------------- 自检
def selftest(N=64, dx=25e-9, verbose=True):
    """★ 预登记自检。返回 True/False（False ⇒ 量具不可信，调用方必须中止）。"""
    ok = True

    def _say(s):
        if verbose:
            print(s)

    _say('=' * 78)
    _say('R461 自检（预登记：判据写死在文件顶部，不在运行时算）')
    _say('=' * 78)

    x = (np.arange(N) + 0.5) * dx
    # ⚠ 必须**铺满三维**：`np.gradient` 要求每一轴都有 ≥ edge_order+1 个元素
    #   （第一版用 `x[:,None,None]` 的形状 (N,1,1) ⇒ `np.gradient` 直接 ValueError）。
    zz, yy, xx = np.meshgrid(x, x, x, indexing='ij')
    X = xx

    # --- 读数的**唯一**实现：带内 median|grad|（4 个带宽）
    def band_med(phi, bands=BANDS):
        g = np.gradient(phi, dx, edge_order=2)
        gm = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
        out = {}
        for b in bands:
            m = np.abs(phi) <= b * dx
            out[b] = float(np.median(gm[m])) if m.any() else float('nan')
            out[('n', b)] = int(m.sum())
        return out, gm

    # ---- T1 平面（正对照）----
    phi = X - 0.5 * N * dx
    r, _ = band_med(phi)
    d1 = abs(r[6.0] - 1.0)
    ok1 = d1 <= TOL_PLANE
    _say('T1 平面 SDF       : med@6dx = %.6f  (真值 1.0, |Δ|=%.2e ≤ %.0e)  %s'
         % (r[6.0], d1, TOL_PLANE, 'PASS' if ok1 else '❌ FAIL'))
    ok &= ok1

    # ---- T2 球（正对照）----
    R = 12 * dx
    rr = np.sqrt((xx - 0.5 * N * dx) ** 2 + (yy - 0.5 * N * dx) ** 2
                 + (zz - 0.5 * N * dx) ** 2)
    phi2 = rr - R
    r2, _ = band_med(phi2)
    d2 = abs(r2[6.0] - 1.0)
    ok2 = d2 <= TOL_SPHERE
    _say('T2 球 SDF         : med@6dx = %.6f  (真值 1.0, |Δ|=%.2e ≤ %.0e)  %s'
         % (r2[6.0], d2, TOL_SPHERE, 'PASS' if ok2 else '❌ FAIL'))
    ok &= ok2

    # ---- T3 抛物（负对照：必须报坏）----
    L = 20 * dx
    phi3 = (X - 0.5 * N * dx) ** 2 / (2.0 * L)
    r3, _ = band_med(phi3)
    ok3 = abs(r3[6.0] - 1.0) > T3_MIN_BAD
    _say('T3 抛物（负对照） : med@6dx = %.6f  (真值≈0.39, 必须 |med−1| > %.1f)  %s'
         % (r3[6.0], T3_MIN_BAD, 'PASS（量具能查出坏场）' if ok3 else '❌ FAIL（量具查不出坏场！）'))
    ok &= ok3

    # ---- T4 平台场（负对照：引擎日志里反复出现的退化形态）----
    #   形态：`seed_plate` 把未播种场写成 `phi_j = max(phi_j, -sdf)`
    #   ⇒ 某一侧被**截成常数**。这里造一个最干净的版本：
    #      `φ = clip(x−x0, −B, +B)`，B = 3dx ⇒ |x−x0|>3dx 处 |∇φ| ≡ 0。
    #   ⚠ 值的范围是 [−3dx,+3dx] ⊂ 带 [−6dx,+6dx] ⇒ **带 = 全域**（见文件头的"预登记更正"）。
    B = 3 * dx
    phi4 = np.clip(X - 0.5 * N * dx, -B, B)
    r4, gm4 = band_med(phi4)
    m4 = np.abs(phi4) <= 6.0 * dx
    frac_flat = float((gm4[m4] < 0.5).mean())
    ok4 = (r4[6.0] <= T4_MED_MAX) and (frac_flat > T4_FRAC_FLAT_MIN)
    _say('T4 平台（负对照） : med@6dx = %.6f (必须 ≤ %.2f)  frac_flat = %.3f '
         '(必须 > %.2f)  %s'
         % (r4[6.0], T4_MED_MAX, frac_flat, T4_FRAC_FLAT_MIN,
            'PASS（量具能查出平台场）' if ok4 else '❌ FAIL（量具查不出平台场！）'))
    ok &= ok4

    # ---- T5 远场截断、但 6dx 带内未被截（正对照）----
    #   ★ 隔离"场真退化"与"带太宽包进了有界远场"这两件事。见文件头的 T5 说明。
    B5 = 20 * dx
    phi5 = np.clip(X - 0.5 * N * dx, -B5, B5)
    r5, gm5 = band_med(phi5)
    m5 = np.abs(phi5) <= 6.0 * dx
    ff5 = float((gm5[m5] < 0.5).mean())
    d5 = abs(r5[6.0] - 1.0)
    ok5 = (d5 <= T5_TOL) and (ff5 <= T5_FRAC_FLAT_MAX)
    _say('T5 远场截断(正对照): med@6dx = %.6f (真值 1.0, |Δ|=%.2e ≤ %.0e)  '
         'frac_flat = %.3f (必须 ≤ %.2f)  %s'
         % (r5[6.0], d5, T5_TOL, ff5, T5_FRAC_FLAT_MAX,
            'PASS（带内未被远场截断污染）' if ok5 else '❌ FAIL'))
    ok &= ok5

    _say('-' * 78)
    _say('★ 自检总结论：%s' % ('**全部 PASS ⇒ 量具可信**' if ok
                              else '❌ **有 FAIL ⇒ 量具不可信，禁止用它出任何读数**'))
    _say('=' * 78)
    return bool(ok)


# ---------------------------------------------------------------- 读数
def _pairs_from_region(reg):
    """按 `region()` 的 6 邻面找**真正相邻**的场配对（与引擎同一口径）。"""
    ps = set()
    for ax in range(3):
        a = np.roll(reg, -1, axis=ax)
        m = reg != a
        if m.any():
            u = np.stack([reg[m], a[m]], 1)
            for p in map(tuple, np.unique(u, axis=0)):
                ps.add((int(min(p)), int(max(p))))
    return sorted(ps)


def measure_snap(z, dx, nreg=None, max_pairs=200, verbose=True):
    """量一个快照。返回 dict（可直接 json.dumps）。"""
    phi = z['phi'] if isinstance(z, np.lib.npyio.NpzFile) else z
    if phi.ndim != 4:
        raise SystemExit('✗ phi 必须是 (nreg,N,N,N)，实际 %s' % (phi.shape,))
    K, N = phi.shape[0], phi.shape[1]
    t0 = time.time()
    out = {'K': int(K), 'N': int(N), 'dx_nm': dx * 1e9}

    # ---- (a) 单场：|∇φ_k| 在**该场自己**的零等值面带内 ----
    single = {b: [] for b in BANDS}
    for k in range(K):
        pk = phi[k]
        if not (pk < 0).any():
            continue                       # 空场（未形核）不算
        g = np.gradient(pk, dx, edge_order=2)
        gm = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
        for b in BANDS:
            m = np.abs(pk) <= b * dx
            if m.any():
                single[b].append(float(np.median(gm[m])))
    out['single'] = {}
    for b in BANDS:
        v = single[b]
        out['single']['%.1f' % b] = {
            'n_fields': len(v),
            'med': float(np.median(v)) if v else float('nan'),
            'p25': float(np.percentile(v, 25)) if v else float('nan'),
            'p75': float(np.percentile(v, 75)) if v else float('nan'),
            'min': float(np.min(v)) if v else float('nan'),
            'max': float(np.max(v)) if v else float('nan'),
        }

    # ---- (b) 配对：|∇d2|，d2 = 0.5(φ_k − φ_l)，**与引擎 reinitialize() 同口径** ----
    reg = np.argmin(phi, axis=0)
    ps = _pairs_from_region(reg)
    out['n_pairs_adj'] = len(ps)
    if len(ps) > max_pairs:
        ps = ps[:max_pairs]
        out['pairs_truncated'] = True
    pair = {b: [] for b in BANDS}
    # 带胞数（band=6dx 口径）—— 用来判断"密微结构 vs 孤立核"
    nband6 = 0
    for (k, l) in ps:
        d2 = 0.5 * (phi[k] - phi[l])
        g = np.gradient(d2, dx, edge_order=2)
        gm = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2)
        for b in BANDS:
            m = np.abs(d2) <= b * dx
            if m.any():
                pair[b].append(float(np.median(gm[m])))
                if b == 6.0:
                    nband6 += int(m.sum())
    out['pair'] = {}
    for b in BANDS:
        v = pair[b]
        out['pair']['%.1f' % b] = {
            'n_pairs': len(v),
            'med': float(np.median(v)) if v else float('nan'),
            'min': float(np.min(v)) if v else float('nan'),
            'max': float(np.max(v)) if v else float('nan'),
            'frac_below_0.95': float(np.mean(np.array(v) < 0.95)) if v else float('nan'),
        }
    out['band6_cells'] = int(nband6)
    out['band6_frac'] = float(nband6) / float(K * N ** 3)
    out['wall_s'] = round(time.time() - t0, 1)
    return out


def _fmt(res, tag):
    L = []
    L.append('--- %s  K=%d N=%d dx=%.1f nm  相邻配对=%d  带胞(6dx)=%d (%.3f%% of K·N³)  用时%.1fs'
             % (tag, res['K'], res['N'], res['dx_nm'], res['n_pairs_adj'],
                res['band6_cells'], 100 * res['band6_frac'], res['wall_s']))
    L.append('    带宽(胞) →   单场 med|∇φ|      (n场)    |   配对 med|∇d2|     (n对)  <0.95占比  min')
    for b in BANDS:
        s = res['single']['%.1f' % b]
        p = res['pair']['%.1f' % b]
        L.append('    %5.1f        %8.4f      (%3d)     |     %8.4f     (%3d)   %6.3f    %.4f'
                 % (b, s['med'], s['n_fields'], p['med'], p['n_pairs'],
                    p['frac_below_0.95'], p['min']))
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--npz', action='append', default=[])
    ap.add_argument('--tag', default=None, help='臂名（在 _exp/_bk_mb 下）')
    ap.add_argument('--root', default='_exp/_bk_mb')
    ap.add_argument('--last', type=int, default=0, help='只量最后 N 帧（0=全部）')
    ap.add_argument('--every', type=int, default=0, help='每 N 帧取一帧（0=全部）')
    ap.add_argument('--dx-nm', type=float, default=None, help='覆盖 dx（默认从 meta.json 读）')
    ap.add_argument('--jsonl', default=None)
    a = ap.parse_args()

    # ★★ 自检先行：不过就不许出读数
    if not selftest(verbose=True):
        print('\n❌ 自检 FAIL ⇒ 按预登记规则，**禁止**用本量具出任何读数。')
        return 2
    print()
    if a.selftest and not a.npz and not a.tag:
        return 0

    files = list(a.npz)
    dx = (a.dx_nm * 1e-9) if a.dx_nm else None
    if a.tag:
        d = os.path.join(a.root, a.tag)
        fs = sorted(glob.glob(os.path.join(d, 'snap_*.npz')),
                    key=lambda f: int(re.search(r'snap_(\d+)\.npz$', f).group(1)))
        if a.every and a.every > 0:
            fs = fs[::a.every]
        if a.last and a.last > 0:
            fs = fs[-a.last:]
        files += fs
        if dx is None:
            mj = os.path.join(d, 'meta.json')
            if os.path.exists(mj):
                with open(mj) as fh:
                    m = json.load(fh)
                # meta 里 dx 的键名各版本不一，逐个找
                for key in ('dx', 'dx_m', 'dx_nm'):
                    if key in m:
                        v = float(m[key])
                        dx = (v * 1e-9) if key == 'dx_nm' else v
                        break
                else:
                    for sect in ('geom', 'config', 'args', 'params'):
                        if isinstance(m.get(sect), dict):
                            if 'dx_m' in m[sect]:
                                dx = float(m[sect]['dx_m']); break
                            if 'dx_nm' in m[sect]:
                                dx = float(m[sect]['dx_nm']) * 1e-9; break
        if dx is None:
            raise SystemExit('✗ 拿不到 dx：请显式给 --dx-nm')

    if not files:
        print('（没有快照可量）')
        return 0
    print('dx = %.4f nm ; 共 %d 个快照' % (dx * 1e9, len(files)))

    recs = []
    for f in files:
        z = np.load(f)
        tag = os.path.basename(os.path.dirname(f)) + '/' + os.path.basename(f)
        res = measure_snap(z, dx)
        res['tag'] = tag
        m = re.search(r'snap_(\d+)\.npz$', f)
        res['step'] = int(m.group(1)) if m else -1
        print(_fmt(res, tag))
        recs.append(res)

    if a.jsonl:
        with open(a.jsonl, 'w') as fh:
            for r in recs:
                fh.write(json.dumps(r, ensure_ascii=False) + '\n')
        print('\n⇒ 逐帧读数已写 %s' % a.jsonl)

    # ---- 趋势（若 >=2 帧）：单场 med@6dx 随时间 ----
    if len(recs) >= 2:
        print('\n--- 趋势：单场 med|∇φ|@6dx / 配对 med|∇d2|@6dx ---')
        print('     step    单场@6dx   配对@6dx   配对@1.5dx  带胞%')
        for r in recs:
            print('  %7d    %8.4f   %8.4f   %8.4f   %6.3f'
                  % (r['step'], r['single']['6.0']['med'], r['pair']['6.0']['med'],
                     r['pair']['1.5']['med'], 100 * r['band6_frac']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
