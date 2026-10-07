#!/usr/bin/env python3
"""_r434_perfield.py —— ★★ **逐场体积/厚度**：是"哪个场"在溶解？

## 为什么这样问
`§191` 查明 A 臂的净驱动力为负（`ΔG_v(T_1) = 1.23e8 < |ed| ≈ 2.5e8`）⇒ `Vt` 下降。
但**谁**在溶解？两种可能，**结论完全不同**：

* **(甲) t=0 那一片（驱动播的、变体 = `laths_eff[0]`）在溶解** ——
  它是**任意变体**（`_seed_next` 用块 0 的轴与变体，**不看 `ed`**）；
  而 `fresh` 通道播的核是按 `--var-rule ed` 选的（最有利变体）。
  ⇒ 若只有场 1 在溶解 ⇒ **问题出在"驱动播种不看驱动力"**，是一处可修的缺口。

* **(乙) 所有场都在溶解（含 `ed` 选的）** ——
  ⇒ 问题出在**整个 athermal 窗口前段驱动力不足**，是 `§191.4` 的框架缺口。

## 量具
`series.csv` 的 `vols` 与 `ths` 列（逐场体积/厚度，`_bk_measure` 产出）。
⚠ 先做**正对照**：`sum(vols)` 是否等于 `Vt`；不等就说明口径不同，要明说。

只读，不写任何归档产物。
"""
import csv
import os
import sys

import numpy as np

BASE = '_exp/_bk_mb'
ARMS = ['dry_abA', 'dry_abB']


def P(s):
    print(s, flush=True)


def parse_list(s):
    """把 `vols` / `ths` 这类列解析成 float 列表。

    ⚠ **自纠错（自查错误 #55）**：第一版只替换了 `[` `]` `,` 与空白，
    而真实格式是**斜杠分隔**（`'0.249512/0/0/…'`，实测 `_r435_rawcols.py`）
    ⇒ 解析结果**恒为空列表**。
    更糟的是第一版的 P-1 正对照写成 `if v and vt > 0` ⇒ **空列表被直接跳过**
    ⇒ 打出"相对差 >5% 的行数 = 0/30"这句**空洞的通过（vacuous pass）**。
    ⇒ 教训（`AGENTS.md` 教训 29）：**先 head 看原始文本，再写解析器**；
      且**正对照必须能失败**（分母为 0 时要报"不适用"，不能报 PASS）。
    """
    if s is None:
        return []
    s = s.strip()
    if not s or s.lower() in ('none', 'nan'):
        return []
    for ch in '[],;':
        s = s.replace(ch, '/')
    out = []
    for tok in s.split('/'):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


P('=' * 100)
P('_r434 —— 逐场体积/厚度：谁在溶解？')
P('=' * 100)

for tag in ARMS:
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        P('\n[%s] ✗ 无 series.csv' % tag)
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    has = 'vols' in rows[0] and 'ths' in rows[0]
    P('\n' + '#' * 100)
    P('# %s（%d 行；vols/ths 在位：%s）' % (tag, len(rows), has))
    P('#' * 100)
    if not has:
        P('  可用列：%s' % ', '.join(rows[0].keys()))
        continue

    # ---- 正对照：sum(vols) vs Vt
    #   ⚠ **自纠错**：第一版写成 `if v and vt > 0` ⇒ 解析失败（空列表）时**静默跳过**
    #     ⇒ 报出"0/30 差异"的**空洞通过**。现在**分母为 0 就报"不适用/FAIL"**。
    P('\n  [P-1 正对照] `sum(vols)` 是否等于 `Vt`？')
    bad = 0
    n_cmp = 0
    for r in rows:
        v = parse_list(r.get('vols'))
        try:
            vt = float(r.get('Vt'))
        except (TypeError, ValueError):
            continue
        if not v:
            continue
        n_cmp += 1
        if vt > 0:
            rel = abs(sum(v) / vt - 1.0)
            if rel > 0.05:
                bad += 1
    if n_cmp == 0:
        P('     可比行数 = **0** ⇒ ❌ **不适用（解析失败）** —— 不得当成 PASS')
    else:
        P('     可比行数 = %d；相对差 >5%% 的行数 = **%d** ⇒ %s'
          % (n_cmp, bad, '✅ 同一口径' if bad == 0 else '⚠ 口径不同'))
    P('     （记账：`vols` 的单位是 **µm³**，不是 m³ —— 实测 `0.249512` = 1 片板条）')

    # ---- 逐场体积（只列非零场）
    P('\n  [逐场体积] 单位 µm³（只列该步非零的场）')
    allf = set()
    for r in rows:
        v = parse_list(r.get('vols'))
        for i, x in enumerate(v):
            if x > 0:
                allf.add(i + 1)
    allf = sorted(allf)
    P('     出现过的场号：%s' % allf)
    P('     %-6s %s' % ('step', ' '.join('%9s' % ('场%d' % k) for k in allf)))
    for r in rows:
        v = parse_list(r.get('vols'))
        cells = []
        for k in allf:
            x = v[k - 1] * 1e18 if k - 1 < len(v) else 0.0
            cells.append('%9.4f' % x)
        P('     %-6s %s' % (r.get('step'), ' '.join(cells)))

    # ---- 逐场趋势：首末对比
    if len(rows) >= 2:
        r0, r1 = rows[0], rows[-1]
        v0, v1 = parse_list(r0.get('vols')), parse_list(r1.get('vols'))
        P('\n  [首末对比] step %s → %s' % (r0.get('step'), r1.get('step')))
        grew, shrank = [], []
        for k in allf:
            a = v0[k - 1] * 1e18 if k - 1 < len(v0) else 0.0
            b = v1[k - 1] * 1e18 if k - 1 < len(v1) else 0.0
            if a <= 0 and b <= 0:
                continue
            tagg = '新生' if a <= 0 else ('**长**' if b > a else '**缩**')
            P('     场%-3d  %8.4f → %8.4f µm³  %s' % (k, a, b, tagg))
            if a > 0:
                (grew if b > a else shrank).append(k)
        P('     ⇒ 播种时就在、且**末态更大**的场：%s' % (grew or '无'))
        P('     ⇒ 播种时就在、且**末态更小**的场：%s' % (shrank or '无'))
        P('     ⇒ 判读：若"缩"的只有场 1（驱动播的那片）⇒ **属(甲)**；'
          '若含 `fresh` 播的场 ⇒ **属(乙)**')
P('=' * 100)
