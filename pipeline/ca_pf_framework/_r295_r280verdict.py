#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""_r295_r280verdict.py —— ★★ **`_r280` 的判决脚本（R-2 / R-3）**：R165 × `--facet-proj 0`。

## 要回答的核心问题（`§145.3` 的三条归因）
R165 实测：把 F2（异变体）最便宜那几对的界面能降 **9.3 倍**，`r_selfac` 只动 **−2.72e-04**。
三条叠加解释：
* **①** `--facet-proj 10` 压制界面能对形态的影响（`§144`/`§147`）
* **②** F2 只占总界面面积 **8.7%**（`§142.1`）
* **③** F2 上界面能项本身只占 `|Δed|` 的 **2–9%**（`§141.1`）

**`_r280` 把 ① 去掉**（`--facet-proj 10 → 0`），其余逐字不动。

## 预登记判据（`_r280` 头部已写死）
* **R-2** ★ 核心：`r_selfac` 末态相对差，与归档的 **−2.72e-04** 比。
  * **≥10×（≈2.7e-3）⇒ ① 是主因**；
  * **仍 ≈2.72e-04 ⇒ ②③ 才是约束。**
* **R-3** `--diag-terms`：无投影时 F2 的 `|stk·κ|/|Δed|` 是否比归档时更大。
* ⚠ **两种结果都有信息量，都必须如实报。**

## 本脚本另外给的**三向对照**（诊断用）
| | λ=0 | λ=1 |
|---|---|---|
| **投影 10（归档）** | `saSet2` | `saSet2F2` |
| **投影 0（新）** | `saSet2P0` | `saSet2F2P0` |
⇒ 既能算"同一投影下的 λ 效应"，也能算"同一 λ 下投影的影响"。
"""
from __future__ import annotations

import csv
import io
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
MB = os.path.join(HERE, '_exp', '_bk_mb')
ARCH = -2.72e-04          # 归档（投影 10）的 r_selfac 末态相对差
SKIP = {'wall_s', 't_wall', 'elapsed_s', 'rss_mb', 'step_s'}


def rows(tag):
    p = os.path.join(MB, 'dry_' + tag, 'series.csv')
    if not os.path.exists(p):
        return None
    with io.open(p, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def last(tag, col):
    r = rows(tag)
    if not r:
        return float('nan')
    try:
        return float(r[-1][col])
    except (KeyError, TypeError, ValueError):
        return float('nan')


def step_of(tag):
    r = rows(tag)
    return int(r[-1]['step']) if r else -1


def coldiff(A, B, upto=None):
    sa = {r['step']: r for r in A}
    sb = {r['step']: r for r in B}
    common = sorted(set(sa) & set(sb), key=lambda x: int(x))
    if upto is not None:
        common = [s for s in common if int(s) <= upto]
    cols = [c for c in A[0] if c in B[0] and c not in SKIP and c != 'step']
    nd_cols, worst = set(), (0.0, None)
    for s in common:
        for c in cols:
            try:
                fa, fb = float(sa[s][c]), float(sb[s][c])
            except (TypeError, ValueError):
                continue
            if fa != fa and fb != fb:
                continue
            if repr(fa) == repr(fb):
                continue
            d = abs(fa - fb) / max(abs(fa), abs(fb), 1e-300)
            nd_cols.add(c)
            if d > worst[0]:
                worst = (d, '%s@step%s' % (c, s))
    return common[-1] if common else None, len(nd_cols), worst


def try_read_zero(tag):
    """读 `diag_terms.json` 里该臂 `vv.n` 的**末值**（权威；`n=0` ⇒ 不适用）。
    返回 int 或 None（无文件/无记录）。"""
    p = os.path.join(MB, 'dry_' + tag, 'diag_terms.json')
    if not os.path.exists(p):
        return None
    try:
        import json
        o = json.load(open(p, encoding='utf-8'))
        rec = o.get('rec') if isinstance(o, dict) else o
        if not rec:
            return None
        return int((rec[-1].get('vv') or {}).get('n', 0))
    except Exception:
        return None


def diag_f2(tag):
    """从 run 日志里取 F2 的 `|stk·κ|/|Δed|` 中位的**末值**。"""
    p = os.path.join(HERE, '_w2_r280_%s_run.log' % tag)
    if not os.path.exists(p):
        return None
    txt = io.open(p, encoding='utf-8', errors='replace').read()
    m = re.findall(r'F2 异变体\s+胞数\s+(\d+)\s+`\|Δed\|` 中位 \*\*([\d.eE+-]+)\*\*'
                   r'（`Δed`≡0 占 ([\d.]+)%）\s+`\|stk·κ\|` 中位 \*\*([\d.eE+-]+)\*\*'
                   r'\s+\*\*比值中位 ([\d.]+)%\*\*', txt)
    if not m:
        return None
    n, med_ed, f0, med_sk, ratio = m[-1]
    return dict(n=int(n), med_ed=float(med_ed), med_sk=float(med_sk),
                ratio=float(ratio))


def main():
    print('=' * 108)
    print('_r295 —— `_r280` 判决：R165 × `--facet-proj 0`（R-2 / R-3）')
    print('=' * 108)
    need = ('saSet2', 'saSet2F2', 'saSet2P0', 'saSet2F2P0')
    for t in need:
        s = step_of(t)
        print('  %-12s 末步 = %s  facet-proj = %s'
              % (t, s, '0' if t.endswith('P0') else '10（归档）'))
    print()
    # ---- R-2 ----
    r0a, r1a = last('saSet2', 'r_selfac'), last('saSet2F2', 'r_selfac')
    r0n, r1n = last('saSet2P0', 'r_selfac'), last('saSet2F2P0', 'r_selfac')
    print('  ## **R-2** `r_selfac` 末态')
    print('     %-26s %-16s %-16s %-14s' % ('组', 'λ=0', 'λ=1', '相对差'))
    d_arch = (r1a - r0a) / r0a if r0a == r0a and r0a else float('nan')
    d_new = (r1n - r0n) / r0n if r0n == r0n and r0n else float('nan')
    print('     %-26s %-16.6f %-16.6f %+.3e' % ('归档（投影 10）', r0a, r1a, d_arch))
    print('     %-26s %-16.6f %-16.6f %+.3e' % ('新（投影 0）', r0n, r1n, d_new))
    print()
    # ★★★ 修（**第 26 个自查错误**）：本脚本第一版**在 step 40 就打了 R-2 终判**
    #   （"❌ ① 不是主因"）—— 而那时 `saSet2P0`/`saSet2F2P0` 只跑到 40/400，
    #   两臂**逐位相同**（相对差 0.000e+00）只是因为**那时还没有 F2 界面**
    #   （`§145.2`：F2 胞数在 step 40 只有 9 个）。
    #   ⇒ **"0×"被我的判据读成"效应一样小"，实际是"还没到能看出效应的时刻"。**
    #   ⇒ 这**正好违反我自己在 `§155.3` 写下的硬规则 ㉚（预先指定终点）**。
    #   ⇒ 现在：**未跑满 400 步 ⇒ 只报中途读数，不出 R-2 判定。**
    END = 400
    s0, s1 = step_of('saSet2P0'), step_of('saSet2F2P0')
    done = (s0 >= END and s1 >= END)
    if not done:
        print('     ⚠ **中途读数（%d / %d 步，终点 %d）⇒ 按硬规则 ㉚ 不出 R-2 判定。**'
              % (min(s0, s1), max(s0, s1), END))
        print('     ⚠ 特别地：**两臂在早期逐位相同是预期的** ——')
        print('        `§145.2` 实测 F2 胞数在 step 40 才 ~9 个、step 80 才上百')
        print('        ⇒ 早期 F2 界面几乎不存在 ⇒ 改它的 γ 自然无效应。')
    if d_new == d_new and d_arch == d_arch and d_arch != 0 and done:
        ratio = abs(d_new) / abs(d_arch)
        print('     ⇒ **|新相对差| / |归档相对差| = %.2f×**' % ratio)
        # ★ 修（第 33 个自查错误附带，`§171.2`）：原来的三分支**没有为"恰好为 0"留位置**
        #   ⇒ ratio=0.00 会落到 `ratio < 3` 的分支，打出"效应仍与归档同量级 / ②③ 才是约束"，
        #     而事实是**一点效应都没有**，那两句话**与事实相反**。
        if abs(d_new) == 0.0 or ratio < 1e-6:
            print('     ⇒ ✅✅ **R-2（第三种结局）：关掉投影后 λ 效应**恰好为零（逐位相同）****')
            print('        ⇒ 这不是"① 不是主因"，而是**更强**的结论：')
            print('          在那条臂上 `--f2-pair-gamma` **完全惰性** ——')
            print('          机制见 `§172`（该臂 `(karr,larr)` 全是同变体 ⇒ F2 的 γ 表无人可查）。')
            print('        ⚠ **不得**把这条读成"②③ 才是约束"（那两句话在此不成立）。')
        elif ratio >= 10:
            print('     ⇒ ✅ **R-2：①（投影压制）是主因** —— 关掉投影后效应放大 ≥10 倍')
        elif ratio >= 3:
            print('     ⇒ ⚠ **部分支持**：放大 %.1f 倍，但不到 10 倍 ⇒ ① 与 ②③ 都有份' % ratio)
        else:
            print('     ⇒ ❌ **R-2：① 不是主因** —— 关掉投影后效应仍与归档同量级')
            print('        ⇒ **②③ 才是约束**（F2 只占 8.7% 面积；其上界面能项只占 2–9%）')
    else:
        if done:
            print('     ⚠ 数据不全或 r_selfac 缺失 ⇒ 无法判')
        # 未跑满时已在上方说明，这里不再重复
    # ---- 三向对照 ----
    print()
    print('  ## 三向对照（诊断：投影对**基线**本身的影响）')
    for lab, a, b in (('λ=0：投影 10 vs 投影 0', 'saSet2', 'saSet2P0'),
                      ('λ=1：投影 10 vs 投影 0', 'saSet2F2', 'saSet2F2P0')):
        A, B = rows(a), rows(b)
        if not A or not B:
            print('     %-26s （缺数据）' % lab)
            continue
        U = min(int(A[-1]['step']), int(B[-1]['step']))
        s, ncol, worst = coldiff(A, B, upto=U)
        print('     %-26s 共同步≤%-5s 不同列 %-4d 最大相对差 %.3e (%s)'
              % (lab, U, ncol, worst[0], worst[1]))
    # ---- R-3 ----
    print()
    print('  ## **R-3** F2 的三项量级（`--diag-terms`，末值）')
    print('     %-14s %-10s %-14s %-14s %s'
          % ('臂', '胞数', '`|Δed|` 中位', '`|stk·κ|` 中位', '`比值中位`'))
    got = {}
    for t in ('saSet2P0', 'saSet2F2P0'):
        d = diag_f2(t)
        got[t] = d
        if d is None:
            # ★ 修（第 33 个自查错误附带）：原版这里一律打"还没出现 F2 的三项读数" ——
            #   **错**：读数**出现了**，是 `胞数 0`（`_stats` 在 `n<20` 时返回 `dict(name,n)`，
            #   `windowB_surface.py:3396-3399`）⇒ 必须把「无记录」与「n=0」分开
            #   （硬规则 ㊳：「没观测到」≠「不存在」）。
            n0 = try_read_zero(t)
            if n0 is not None:
                print('     %-14s **胞数 %d** ⇒ ⚪ **不适用**（`advance` 的 `(karr,larr)` '
                      '基里没有异变体面片，见 `§170`）' % (t, n0))
            else:
                print('     %-14s （日志里确实没有 F2 的任何读数）' % t)
            continue
        print('     %-14s %-10d %-14.4e %-14.4e **%.2f%%**'
              % (t, d['n'], d['med_ed'], d['med_sk'], d['ratio']))
    print('     ⇒ 归档（`§141.1`/`§145.2`）的 F2 比值中位 ~**2–9%** ⇒ 与之比：')
    for t, d in got.items():
        if d:
            print('        %-14s 末值 **%.2f%%** %s'
                  % (t, d['ratio'],
                     '⇒ **更大**（界面能项在无投影时更"活"）' if d['ratio'] > 9
                     else '⇒ 与归档同量级'))
    print()
    print('  ⚠ 记账：`saSet2P0`/`saSet2F2P0` 必须**跑满 400 步**才作终判；')
    print('     未跑满时本脚本给出的是中途读数（硬规则 ㉚）。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
