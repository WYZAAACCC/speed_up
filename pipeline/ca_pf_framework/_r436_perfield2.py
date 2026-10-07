#!/usr/bin/env python3
"""_r436_perfield2.py —— ★★★★ **逐场 × 逐变体**：谁长、谁溶？（`§193` 的主量具）

## 为什么
`_r434`（解析器修好后）已看到：
* **abA**：**每一个场都在溶解**，**含 `fresh` 通道按 `--var-rule ed` 播的场**（7、13）；
* **abB**：**有的长、有的溶** —— 长的似乎是**特定变体**（目测 V7、V11），
  溶的似乎全是 **V1**。

若这条成立，它就是 `§191` 机理的**逐变体证据**，而且直接指向**可修的缺口**：
**`--var-rule ed` 选的是"当刻最优"，但早期 ΔG_v 太小 ⇒ 当刻最优也不够 ⇒ 溶解。**

## 口径（先写死）
* `vols` 的单位是 **µm³**（实测 `0.249512` = 1 片 1000×500×510 nm 板条）。
  ⚠ **自查错误 #56**：`_r434` 把它当成 SI(m³) 又乘了 1e18 ⇒ 显示成 2.5e17。
  **比值不受影响，但显示必须改。**
* 场→变体来自 `meta.json` 的 `vmap`。
* 判据：**末态体积 > 首次出现时的体积 ⇒ 长**；**< ⇒ 溶**。
  ⚠ 首次出现那一行本身就是"刚播下"，所以用它做基准。
"""
import csv
import json
import os
import sys

import numpy as np

BASE = '_exp/_bk_mb'
ARMS = [('dry_abA', 'A 守 C-3'), ('dry_abB', 'B burst')]


def P(s):
    print(s, flush=True)


def parse_list(s):
    """斜杠分隔（`_r435` 实测）；**空串要返回 []，且调用方必须能识别"解析失败"**。"""
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


P('=' * 104)
P('_r436 —— 逐场 × 逐变体：谁长、谁溶？')
P('=' * 104)

for tag, desc in ARMS:
    p = os.path.join(BASE, tag, 'series.csv')
    mp = os.path.join(BASE, tag, 'meta.json')
    if not os.path.exists(p):
        P('\n[%s] ✗ 无 series.csv' % tag)
        continue
    rows = list(csv.DictReader(open(p, newline='')))
    vmap = {}
    if os.path.exists(mp):
        vmap = {int(k): int(v) for k, v in json.load(open(mp)).get('vmap', {}).items()}

    P('\n' + '#' * 104)
    P('# %s（%s）  step 0→%s' % (tag, desc, rows[-1].get('step')))
    P('#' * 104)

    # 逐场时间序列
    series = {}
    for r in rows:
        st = int(float(r['step']))
        v = parse_list(r.get('vols'))
        for i, x in enumerate(v):
            k = i + 1
            if x > 0:
                series.setdefault(k, []).append((st, x))
    if not series:
        P('  ❌ 解析后没有任何非零场 ⇒ **量具失效**，不得当成结论')
        continue

    P('\n  %-5s %-6s %-9s %-11s %-11s %-11s %-9s %s'
      % ('场', '变体', '首次步', '首体积', '峰值', '末体积', '寿命(步)', '判读'))
    grow, diss = [], []
    for k in sorted(series):
        s = series[k]
        st0, v0 = s[0]
        vmax = max(x for _, x in s)
        vend = s[-1][1]
        st_end = s[-1][0]
        v = vmax > v0 * 1.15
        w = vmax < v0 * 0.85 or (v0 > 1e-6 and vmax < v0)
        if vmax > v0 * 1.15:
            verdict = '**长**'
            grow.append((k, vmap.get(k)))
        elif vmax < v0 * 0.85:
            verdict = '**溶**'
            diss.append((k, vmap.get(k)))
        else:
            verdict = '平'
        P('  %-5d %-6s %-9d %-11.4f %-11.4f %-11.4f %-9d %s'
          % (k, vmap.get(k, '?'), st0, v0, vmax, vend, st_end - st0, verdict))

    P('\n  【汇总】**长**的场：%s' % (grow or '无'))
    P('        **溶**的场：%s' % (diss or '无'))
    gv = sorted({v for _, v in grow if v is not None})
    dv = sorted({v for _, v in diss if v is not None})
    P('        **长**的场用到的变体：%s' % gv)
    P('        **溶**的场用到的变体：%s' % dv)
    if gv and dv:
        if not set(gv) & set(dv):
            P('        ⇒ ✅ **变体完全分离**：长的全是 %s，溶的全是 %s'
              % (gv, dv))
        else:
            P('        ⇒ ⚠ 变体**有交叠**（%s）⇒ "某些变体不利"这条**不成立**，须另找解释'
              % sorted(set(gv) & set(dv)))
    P('        ⇒ 判读：')
    P('          · 若"溶"里**含 `fresh` 播的场** ⇒ 不是"驱动播了任意变体"那么简单；')
    P('          · 若长的场**首次步都更晚** ⇒ 支持"`ΔG_v` 随时间上升 ⇒ 晚播的才活得下来"。')
    late_g = [series[k][0][0] for k, _ in grow]
    late_d = [series[k][0][0] for k, _ in diss]
    if late_g and late_d:
        P('          实测首次步：长的中位 **%d**，溶的中位 **%d** ⇒ %s'
          % (int(np.median(late_g)), int(np.median(late_d)),
             '✅ 晚播的更容易活' if np.median(late_g) > np.median(late_d)
             else '⚠ 与"晚播更容易活"不符'))
P('=' * 104)
