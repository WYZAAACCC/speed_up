#!/usr/bin/env python3
"""_r441_turn.py —— ★ 两支臂的 **Vt 转折点**：`§191.5` 的预言对不对？

`§191.5` 预言（**跑之前写死**）：`abA` 的 `Vt` 应在 **step ≈ 3000–3200** 由降转升。
`§195.6` 已提示这条**可能不成立**（因为"门槛是常数"的前提本身就有问题，见自查错误 #54）。

本脚本用**滑动窗口**找转折点，并对**两条臂**都做，避免只看一条。

判据：
  * 转折点 = 滑动窗口中位斜率**首次由负转正且此后不再回到负**的步号；
  * 报出 `abA` 的实测转折点与预言的比值。
"""
import csv
import os

import numpy as np

BASE = '_exp/_bk_mb'


def P(s):
    print(s, flush=True)


def load(tag):
    p = os.path.join(BASE, tag, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, newline='')))
    st, vt = [], []
    for r in rows:
        try:
            st.append(int(float(r['step'])))
            vt.append(float(r['Vt']))
        except (TypeError, ValueError):
            pass
    return np.array(st), np.array(vt)


P('=' * 88)
P('_r441 —— Vt 转折点（检验 `§191.5` 的预言：abA 应在 step≈3000–3200 转升）')
P('=' * 88)

for tag, pred in (('dry_abA', 3100), ('dry_abB', 190)):
    d = load(tag)
    if d is None:
        P('\n[%s] ✗ 无 series.csv' % tag)
        continue
    st, vt = d
    P('\n[%s]  %d 行，step %d → %d' % (tag, len(st), st[0], st[-1]))
    # 滑动窗口中位斜率（窗口 = 5 个采样点）
    W = 5
    turn = None
    slopes = []
    for i in range(len(st) - W + 1):
        y = vt[i:i + W]
        x = st[i:i + W].astype(float)
        sl = float(np.polyfit(x, y, 1)[0])
        slopes.append((int(st[i]), sl))
    for j, (s0, sl) in enumerate(slopes):
        if sl > 0 and all(s2 > 0 for _, s2 in slopes[j:]):
            turn = s0
            break
    P('  逐段斜率（每 5 点）：%s'
      % ', '.join('%d:%+.2e' % (s, v) for s, v in slopes[:12]))
    P('  … 末段：%s' % ', '.join('%d:%+.2e' % (s, v) for s, v in slopes[-4:]))
    if turn is None:
        P('  ⇒ **尚未出现"此后一直为正"的转折点**（仍在溶解或锯齿中）')
    else:
        P('  ⇒ 实测转折点 ≈ **step %d**；`§191.5` 预言 %d ⇒ 实测/预言 = **%.2f**'
          % (turn, pred, turn / pred))
    P('  ⇒ 末态 Vt = %.5f µm³（首 %.5f）⇒ %+.1f%%'
      % (vt[-1] * 1e18, vt[0] * 1e18, 100 * (vt[-1] / vt[0] - 1)))
    P('  Vt 轨迹（每 5 个采样取 1）：')
    P('    %s' % ' '.join('%.4f' % (x * 1e18) for x in vt[::5]))
P('=' * 88)
