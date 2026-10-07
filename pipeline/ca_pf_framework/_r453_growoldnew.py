#!/usr/bin/env python3
"""_r453_growoldnew.py —— ★★★★★ **以前长、现在不长？** 逐根对比新旧算例

## 用户的问题
> 之前测试的时候长吗？现在测试为什么不长？

## 为什么我上一条回答可能误导
我用了**平均体积 / 播种体积**（三因子里的 ③）说"基本没长"。
但**新形核的核一开始就很小**，会把平均值**稀释** ⇒
**平均值停在 1.0 不代表"老板条没长"**。
⇒ 必须**逐根**看：拿**最早播下的那根**（场 1），看它自己的体积怎么变。

## 对比对象
* **旧**：`dry_saSet2`（归档；**12 根 t=0 全部播种**、`df = 常数 3.5e8`、400 步）
* **新**：`dry_abA` / `dry_abB`（**逐根形核**、`df = ΔG_v(T)` 从 1.23e8 起、5922/800 步）

## 判据
**G-1** 逐根给出**生长倍数**（末值/首值）与**体积增长速率**。
**G-2** 把新臂的场 1 与旧臂的场 1 并排比（**同一根板条**的角色）。
**G-3** 报出 `df`（驱动力）的差别 —— 这是**最可能的解释**。
"""
import csv
import json
import os

import numpy as np

BASE = '_exp/_bk_mb'
CASES = [('dry_saSet2', '旧：12 根全部 t=0 播种，df=常数 3.5e8'),
         ('dry_abA', '新：逐根形核，df=ΔG_v(T)'),
         ('dry_abB', '新：逐根形核，df=ΔG_v(T)')]


def P(s):
    print(s, flush=True)


def parse_list(s):
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
        if tok:
            try:
                out.append(float(tok))
            except ValueError:
                pass
    return out


P('=' * 104)
P('_r453 —— 「以前长、现在不长？」逐根对比')
P('=' * 104)

for tag, desc in CASES:
    p = os.path.join(BASE, tag, 'series.csv')
    mp = os.path.join(BASE, tag, 'meta.json')
    if not os.path.exists(p):
        P('\n[%s] ✗ 无 series.csv（可能已被删）' % tag)
        continue
    m = json.load(open(mp)) if os.path.exists(mp) else {}
    ea = m.get('exp_args', {})
    P('\n' + '#' * 104)
    P('# %s —— %s' % (tag, desc))
    P('   N=%s  steps=%s  df_const=%s  nuc_law=%s  alpha_km=%s  beta_h=%s'
      % (m.get('N'), ea.get('steps'), m.get('df_const'), ea.get('nuc_law'),
         ea.get('alpha_km'), ea.get('beta_h')))
    P('#' * 104)

    rows = list(csv.DictReader(open(p, newline='')))
    # 逐场轨迹（体积，µm³）
    traj = {}
    steps = []
    for r in rows:
        try:
            st = int(float(r['step']))
        except (TypeError, ValueError):
            continue
        v = parse_list(r.get('vols'))
        if not v:
            continue
        steps.append(st)
        for i, x in enumerate(v):
            if x > 1e-9:
                traj.setdefault(i + 1, []).append((st, x))
    if not traj:
        P('  ✗ 解析不到逐场体积')
        continue
    P('\n  %-5s %-7s %-9s %-11s %-11s %-11s %s'
      % ('场', '首步', '首体积', '末体积', '峰值', '生长倍数', '存活步数'))
    for k in sorted(traj):
        s = traj[k]
        v0 = s[0][1]
        v1 = s[-1][1]
        vmax = max(x for _, x in s)
        P('  %-5d %-7d %-9.4f %-11.4f %-11.4f %-11.2f %d'
          % (k, s[0][0], v0, v1, vmax, vmax / max(v0, 1e-12), s[-1][0] - s[0][0]))
    # 场 1 重点
    if 1 in traj:
        s = traj[1]
        P('\n  ★ **场 1（最早那根）轨迹**：%s'
          % ' '.join('%.3f' % x for _, x in s[:14]))
        P('     %d 个采样；首 %.4f → 末 %.4f µm³ ⇒ **%.2f×**'
          % (len(s), s[0][1], s[-1][1], s[-1][1] / max(s[0][1], 1e-12)))
        if len(s) >= 4:
            d = np.diff([x for _, x in s])
            P('     逐步增量（前 12 个）：%s'
              % ' '.join('%+.4f' % x for x in d[:12]))
P('=' * 104)
P('[看点] 最可能的解释：**驱动力不同**')
P('  旧臂 `df_const = 3.5e8`（常数，= ΔG_v(298 K)）')
P('  新臂 `df = ΔG_v(T)`，起点 T_1=849 K 时只有 **1.23e8** ⇒ 小 **2.85 倍**')
P('  ⇒ 若新臂早期的生长速率 ≈ 旧臂的 1/2.85，就说明**不是"不长"，是"驱动力小、长得慢"**。')
P('=' * 104)
