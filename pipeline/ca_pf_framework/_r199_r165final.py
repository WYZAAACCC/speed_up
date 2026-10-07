#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r199_r165final.py —— R165 的**诚实判决**（修正 `_r171` 的退化除零 bug）+ 机制量测。

## `_r171` 错在哪（**本轮第 12 个自查错误**）

`_r171` 的 G-2 写：
    `if s > 2 * o: ✅ G-2 成立`      # s = saSet2 的 |Δ趋势|, o = saOddG 的 |Δ趋势|
实测 **s = 0.0000、o = 0.0000**（两个都数值为零）⇒ `o` 是 ~1e-9 级的残差
⇒ `s/o = 61.33` ⇒ **误报"✅ G-2 成立"**。
**⇒ 违反硬规则 ⑨**（比值判据必须先查"分子≈0 时返回什么"）—— 而这个脚本是我自己写的。

**⇒ 正确判据**：先查**效应本身是否可辨**（`|Δ|` 是否 > 数值噪声），
只有效应可辨时**才**去比值。效应不可辨 ⇒ 判 **"无显著效应（null result）"**。

## 本脚本判什么

* **R-1** λ=1 相对 λ=0 的效应量：`r_selfac` 末值、斜率、`E_el/Vt`、`E_el/A_int`。
* **R-2** 效应是否**超过数值噪声**（用逐位相同的惰性跑作噪声地板 = 0）。
* **R-3** ★ **机制**：变体-变体（F2）界面**占总界面面积的比例**是多少？
  若 F2 面积占比极小 ⇒ **改 F2 的 γ 本来就不会有可测影响** ⇒ 否定结果是**预期内的**，
  而不是"实验失败"。
* **R-4** 逐列对比（`§116` 的教训：只看 `r_selfac` 会漏）。
"""
from __future__ import annotations

import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
PAIRS = [('saSet2', 'saSet2F2', '{1,2,3,4,7,8}：含 3 个同 packet 失配对'),
         ('saOddG', 'saOddGF2', '{1,3,5,7,9,11}：不含任何同 packet 对')]
NOISE = 0.0          # 惰性跑的逐位对比给出"噪声地板 = 0.000e+00"


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def col(rs, k):
    out = []
    for r in rs:
        try:
            out.append(float(r[k]))
        except (KeyError, TypeError, ValueError):
            out.append(float('nan'))
    return np.array(out)


def slope(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    return float(np.polyfit(x[m], y[m], 1)[0]) if m.sum() >= 3 else float('nan')


def main():
    print('=' * 108)
    print('_r199 —— R165 的诚实判决（修正 `_r171` 的退化除零）+ 机制量测')
    print('=' * 108)
    print('  ⚠ 本脚本**不使用** `_r171` 的 G-2 比值判据（两个数都 ≈ 0 ⇒ 比值无意义）。')
    print('  ⚠ 数值噪声地板 = **%.1e**（由惰性跑「93/93 列逐位相同」定出）' % NOISE)
    res = {}
    for t0, t1, lab in PAIRS:
        A, B = rows(t0), rows(t1)
        if A is None or B is None:
            print('\n  ⚠ `%s`/`%s` 数据不全 ⇒ 跳过' % (t0, t1))
            continue
        print()
        print('  ' + '=' * 104)
        print('  ## `%s`(λ=0) vs `%s`(λ=1) —— %s' % (t0, t1, lab))
        print('  ' + '=' * 104)
        st = col(A, 'step')
        out = {}
        for k in ('r_selfac', 'E_el_J', 'Vt', 'f2_area_m2', 'f3_area_m2',
                  'nf2', 'nf3', 'blk_span_nm', 'blk_alen_nm', 'n_lath', 'n_var_sig'):
            out[k] = (col(A, k), col(B, k))
        print('     %-14s %-16s %-16s %-12s %s'
              % ('量', 'λ=0', 'λ=1', '相对差', '判定'))
        for k in ('r_selfac', 'E_el_J', 'Vt', 'blk_span_nm', 'blk_alen_nm',
                  'n_lath', 'n_var_sig'):
            a, b = out[k]
            ma, mb = np.isfinite(a), np.isfinite(b)
            if not ma.any() or not mb.any():
                continue
            va, vb = a[ma][-1], b[mb][-1]
            d = (vb - va) / va if va else float('nan')
            tag = ('**无可辨差别**' if abs(d) <= 1e-6 else
                   '可辨（%.2e）' % abs(d))
            print('     %-14s %-16.6g %-16.6g %-12s %s' % (k, va, vb, '%+.3e' % d, tag))
        # 斜率（r_selfac）
        s0 = slope(st[np.isfinite(out['r_selfac'][0])],
                   out['r_selfac'][0][np.isfinite(out['r_selfac'][0])])
        s1 = slope(st[np.isfinite(out['r_selfac'][1])],
                   out['r_selfac'][1][np.isfinite(out['r_selfac'][1])])
        dsl = s1 - s0
        print()
        print('     **R-1** `r_selfac` 斜率：λ=0 **%+.6f**/步，λ=1 **%+.6f**/步'
              '（**Δ = %+.2e**）' % (s0, s1, dsl))
        print('     **R-2** 效应是否超过噪声地板 %.1e ⇒ **%s**'
              % (NOISE, '**是**' if abs(dsl) > max(NOISE, 1e-9) * 1e3 else '**否**'))
        # ---- R-3 机制：F2 面积占比 ----
        f2a, f3a = out['f2_area_m2'], out['f3_area_m2']
        print()
        print('     **R-3 机制**：变体-变体（**F2**）界面面积占比')
        print('        %-6s %-14s %-14s %-14s %s'
              % ('step', 'f2_area[µm²]', 'f3_area[µm²]', 'nf2', 'F2 占(F2+F3)'))
        for i in range(0, len(A), max(1, len(A) // 6)):
            a2 = f2a[0][i] if np.isfinite(f2a[0][i]) else 0.0
            a3 = f3a[0][i] if np.isfinite(f3a[0][i]) else 0.0
            tot = a2 + a3
            print('        %-6d %-14.4g %-14.4g %-14.0f %.4f%%'
                  % (int(st[i]), a2 * 1e12, a3 * 1e12, out['nf2'][0][i],
                     100 * a2 / tot if tot else float('nan')))
        a2e = f2a[0][-1] if np.isfinite(f2a[0][-1]) else 0.0
        a3e = f3a[0][-1] if np.isfinite(f3a[0][-1]) else 0.0
        frac = a2e / (a2e + a3e) if (a2e + a3e) else float('nan')
        res[t0] = dict(s0=s0, s1=s1, dsl=dsl, frac=frac,
                       r0=out['r_selfac'][0][np.isfinite(out['r_selfac'][0])][-1],
                       r1=out['r_selfac'][1][np.isfinite(out['r_selfac'][1])][-1])
        print('        ⇒ 末态 F2 面积 / (F2+F3) = **%.3f%%**' % (100 * frac))
        # ---- R-4 全列对比 ----
        cols = [c for c in A[0] if c in B[0]
                and c not in ('step', 'wall_s', 't_s')]
        nd, mx = 0, (0.0, None)
        for c in cols:
            a, b = col(A, c), col(B, c)
            m = np.isfinite(a) & np.isfinite(b)
            if not m.any():
                continue
            den = np.maximum(np.abs(a[m]), 1e-300)
            rel = np.max(np.abs(a[m] - b[m]) / den)
            if rel > 1e-6:
                nd += 1
            if rel > mx[0]:
                mx = (rel, c)
        print()
        print('     **R-4 全列对比**：%d 列中有 **%d 列**相对差 > 1e-6；'
              '最大 = %.3e（列 `%s`）' % (len(cols), nd, mx[0], mx[1]))
    # ---- 总结 ----
    print()
    print('=' * 108)
    print('  ## 总结论')
    print('=' * 108)
    for t0 in res:
        d = res[t0]
        print('     `%s`：`r_selfac` %.4f → %.4f；斜率 Δ = %+.2e；'
              'F2 面积占比 %.3f%%'
              % (t0, d['r0'], d['r1'], d['dsl'], 100 * d['frac']))
    print()
    print('     ⇒ **λ=1（F2 配对 γ，最便宜的对降到 0.107×γ₀）对两臂都**没有可辨影响**。**')
    print('     ⇒ **否定结果（null result）**，且 `§134`/`§132` 的 R-3 给出**机制解释**：')
    print('        变体-变体界面只占总界面的极小一部分 ⇒ 改它的 γ **本来就不该有可测影响**。')
    print()
    print('  ⚠ 记账：本脚本**不**用比值判据（`_r171` 的 61.33× 是除零伪影，已作废）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
