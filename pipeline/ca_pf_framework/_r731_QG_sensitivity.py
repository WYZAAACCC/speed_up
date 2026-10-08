#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r731_QG_sensitivity.py —— **T3：把 `Π`/`q*` 判据改写成对 `Q_G` 区间的敏感性**。

> **用户决定（2026-10-08）**：「**（3）暂时降级为敏感性**」
> **依据**：`R712 §6.2`（`Π`/`q*` 判据）＋ `R724`（Ti64 的 `Q_G` 缺口经 217 篇确认为真）
> **纪律**：`R629 E1`（**零主代码改动**，只加只读脚本）；**不跨合金拟合**（`R712 §0.3` 的 E7 教训）

---

## 判据原文（`R712 §6.2`，逐字保留）
```
v(T) = v(1100 K)·exp[−(Q_G/R)(1/T − 1/1100)]
判据：Π ≡ n·(v/q)³ ≫ 1   ⇔   instantaneous growth 成立
等价：q* = v(T)·n^(1/3)   （临界冷速）
```
`[文]`（全部来自 **Liu 2015 = Fe–0.7at%Al**）：`Q_G = 8.2 ± 1.5 kJ/mol`、
`v(1100 K) = 4.1e-4 m/s`、`:875-876`"the γ/α′ interface possesses a **very high mobility**"。

## ★ 本次要解决的**规范缺口**（`R724 §4` 已登记）
`R712 §6.2` 只给了 `Q_G` 的**单点值**。Ti64 无实测 ⇒ 本脚本把结论改成
**"在 `Q_G ∈ [5,15] kJ/mol` 的整个区间内，`Π`/`q*` 落在什么范围"**，
并**显式标注哪些工况的结论对 `Q_G` 敏感、哪些不敏感**。

## 口径（**写死；含两处必须记账的假设**）
* `R = 8.314 J/(mol·K)`
* `v(T) = v1100·exp[−(Q_G/R)(1/T − 1/1100)]`（Arrhenius，锚在 1100 K）
* `q* = v(T)·n^(1/3)`（`n` = 板条数密度 m⁻³，**`[待标定]`**，取 `R721` 标定链的示例值扫）
* ⚠ **假设 1**：`Π ≡ n·(v/q)³` 里的 `q` 是**冷速 K/s**（`R712 §6.2` 的上下文如此），
  故 `Π` 无量纲。**规范未逐字定义 `q`，此处按上下文取冷速。**
* ⚠ **假设 2**：`R712 §6.2` 给的推导中间量 `t_nuc = 1/(a·q·V_ev)` 里的 `V_ev`
  **规范未定义**。本脚本**不重建 `Π` 的推导**，只按 `R712` 已给的**等价式 `q* = v·n^(1/3)`**
  计算，并把 `Π` 作为 `(q*/q)³` 报出（两者等价：`Π = (q*/q)³`）。

## 用法
    python3 _r731_QG_sensitivity.py
    python3 _r731_QG_sensitivity.py --n 3.17e17 --q 1e3 1e4 1e5 1e6 1e7 1e8
"""
import argparse
import sys

import numpy as np

R = 8.314
V1100 = 4.1e-4        # m/s，Liu 2015（Fe–0.7Al）


def v_of_T(T, QG):
    """`v(T) = v1100·exp[−(Q_G/R)(1/T − 1/1100)]`（`Q_G` 单位 J/mol）。"""
    return V1100 * np.exp(-(QG / R) * (1.0 / np.asarray(T, float) - 1.0 / 1100.0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=float, default=3.174415e17,
                    help='板条数密度 m^-3（默认取 R721 标定链的示例值）')
    ap.add_argument('--q', type=float, nargs='*',
                    default=[1e3, 1e4, 1e5, 1e6, 1e7, 1e8],
                    help='冷速 K/s（LPBF 典型 1e3–1e8）')
    ap.add_argument('--T', type=float, nargs='*', default=[600.0, 873.0, 1100.0])
    a = ap.parse_args()

    QG_LO, QG_MID, QG_HI = 5.0e3, 8.2e3, 15.0e3      # J/mol
    print('=' * 104)
    print('T3：`Pi`/`q*` 对 `Q_G` 的**敏感性**（不引用绝对数、不跨合金拟合）')
    print('=' * 104)
    print('  `Q_G` 区间 = **[5.0, 15.0] kJ/mol**（中值 8.2 = Liu 2015 的 Fe–0.7Al 值，仅作锚）')
    print('  `v(1100 K) = %.2e m/s`（同上，**Fe 基，非 Ti64**）' % V1100)
    print('  `n = %.4e m^-3`（`R721` 标定链示例值；**真值 [待标定]**）' % a.n)
    print('  ⚠ 两处假设见 docstring：`q` = 冷速 K/s；`Pi = (q*/q)^3`')
    print()

    print('  ## 1) `q* = v(T)·n^(1/3)` —— 临界冷速（K/s）')
    print('  %-9s %14s %14s %14s %10s' %
          ('T (K)', 'Q_G=5', 'Q_G=8.2', 'Q_G=15', '区间/中值'))
    for T in a.T:
        qs = [v_of_T(T, Q) * a.n ** (1.0 / 3.0) for Q in (QG_LO, QG_MID, QG_HI)]
        print('  %-9.1f %14.4g %14.4g %14.4g %10.2f'
              % (T, qs[0], qs[1], qs[2], qs[2] / max(qs[0], 1e-300)))
    print('  ⇒ `q*` 随 `Q_G` **单调降**；区间跨度（5→15）见最后一列')
    print()

    print('  ## 2) ★ `Pi = (q*/q)^3` —— 逐工况判定（`Pi >> 1` = 生长不受限）')
    print('  %-9s %-10s %12s %12s %12s %-22s' %
          ('T (K)', 'q (K/s)', 'Pi(Q=5)', 'Pi(Q=8.2)', 'Pi(Q=15)', '判定（跨整个 Q_G 区间）'))
    rows = []
    for T in a.T:
        for q in a.q:
            pis = [(v_of_T(T, Q) * a.n ** (1.0 / 3.0) / q) ** 3
                   for Q in (QG_LO, QG_MID, QG_HI)]
            lo, mid, hi = pis
            if lo > 10:
                verdict = '✅ 全区间 Pi>>1（结论不敏感）'
            elif hi < 0.1:
                verdict = '⛔ 全区间 Pi<<1（结论不敏感）'
            else:
                verdict = '🟡 **对 Q_G 敏感**（区间跨 1）'
            rows.append((T, q, lo, mid, hi, verdict))
            print('  %-9.1f %-10.3g %12.3g %12.3g %12.3g %s'
                  % (T, q, lo, mid, hi, verdict))
    print()
    n_sens = sum(1 for r in rows if r[5].startswith('🟡'))
    n_ok = sum(1 for r in rows if r[5].startswith('✅'))
    n_no = sum(1 for r in rows if r[5].startswith('⛔'))
    print('  ## 3) 汇总（⚠ 计数标签已修：第一版用子串 "敏感" 匹配 ⇒「不敏感」也被计入）')
    print('     结论**稳健**（`Q_G ∈ [5,15]` 全区间同向）：**%d / %d**'
          '（其中 `Pi>>1` 有 %d、`Pi<<1` 有 %d）' % (n_ok + n_no, len(rows), n_ok, n_no))
    print('     结论**对 `Q_G` 敏感**（区间跨 1）：**%d / %d**' % (n_sens, len(rows)))
    print()
    print('  ## 4) ★★ 最要紧的一条：**本表全部 %d 个工况都是 `Pi << 1`**' % len(rows))
    print('     ⇒ `Pi` 最大也只有 **%.4g**（T=1100 K、q=10³ K/s）' % max(r[4] for r in rows))
    print('     ⇒ **按 Liu 2015 的界面迁移率，LPBF 的冷速区间（10³–10⁸ K/s）全部落在')
    print('        "生长受限"一侧**，而 `R712 §6.2` 的框架（`instantaneous growth`）')
    print('        **是建立在这个近似成立的前提上的** ⇒ ⚠ **前提不成立**')
    print()
    print('  ## 5) `n` 的敏感性（`n` 是 `[待标定]` ⇒ 必须扫）')
    print('     `q* = v·n^(1/3)` ⇒ `q* ∝ n^(1/3)`；`n` 差 100 倍 ⇒ `q*` 只差 **%.2f 倍**'
          % (100.0 ** (1.0 / 3.0)))
    print('     %-14s %14s %14s' % ('n (m^-3)', 'q*@873K(Q_G=8.2)', 'Pi@q=1e5'))
    for nn in (1e16, 1e17, 3.17e17, 1e18, 1e19):
        qs = v_of_T(873.0, QG_MID) * nn ** (1.0 / 3.0)
        pi = (qs / 1e5) ** 3
        print('     %-14.3g %14.4g %14.4g' % (nn, qs, pi))
    print('     ⇒ 即便 `n` 变 1000 倍，`Pi@1e5` 也只从 %.3g 变到 %.3g —— **仍在 `<<1`**'
          % ((v_of_T(873.0, QG_MID) * 1e16 ** (1.0 / 3.0) / 1e5) ** 3,
             (v_of_T(873.0, QG_MID) * 1e19 ** (1.0 / 3.0) / 1e5) ** 3))
    print()
    print('  ⚠ **诚实边界**：')
    print('     · `Q_G`/`v(1100K)` **都是 Fe 基合金**（`R724` 已用 217 篇确认 Ti64 无实测）')
    print('     · `n` 是 `[待标定]`（`R712 §10.4`；用户指示板条几何暂不定稿）')
    print('     · 故本表**只能判"哪些工况的结论稳健、哪些不稳健"**，')
    print('       **不能**给任何"Ti64 在某冷速下是/不是形核控制"的绝对结论')
    print('     · `Pi` 的推导中间量 `V_ev` 规范未定义 ⇒ 本脚本用等价的 `(q*/q)^3`')
    return 0


if __name__ == '__main__':
    sys.exit(main())
