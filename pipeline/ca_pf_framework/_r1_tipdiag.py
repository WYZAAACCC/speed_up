#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_tipdiag.py --- ★ 最后一个未解问题：**为什么没有平端面**（单核 C-5 未达标的根因）

事实
----
单核 `lath`/`mid` 在 R24 上的 `f_a`（界面里 `|n·a|>0.9` 的面积占比）只有 **0.2–3%**，
而**种子本身就是棱柱**（端面严格垂直 `a`）。⇒ 平端面**在演化中丢掉了**。
这直接导致 C-5（`fill_cal` ≥0.70）未达标：形状是"圆角板"而不是矩形板条。

两个竞争假说（必须分开）
------------------------
  H-1 **数值圆化**：level-set 平流的数值扩散把尖角磨圆
      ⇒ `f_a` 应当在**最初几步内**从种子值**迅速**掉到 ~0，且与 `norm_smooth` 无关。
  H-2 **动力学圆化**：`M(n)` 的谷底在 `n ∥ n*`/`n ∥ w`，端面（`n ∥ a`）的 M 最大
      ⇒ 端面边缘的斜界面长得比端面中心快 ⇒ 端面自然鼓成圆帽。
      ⇒ `f_a` 的衰减应当**慢**、且**依赖 `norm_smooth`**（因为它改变 M 的锐度）。

判据（先写死）
--------------
  * 若 `f_a` 在 **≤5 步**内从种子值掉到 <1/3 ⇒ **H-1 主导**（数值）。
  * 若 `f_a` 在 **数十步**内缓慢衰减 ⇒ **H-2 主导**（动力学）。
  * 两条都要看：`f_n`（宽面）与 `f_w`（侧面）是否**保持**（它们应当保持，
    因为宽面是 M 的谷底、最稳定）。

数据源：`_exp/<name>/series.csv` 的 `f_a/f_w/f_n` 列（每 4 步一采样）。
"""
import os
import csv
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load(d):
    p = os.path.join(HERE, d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    out = {}
    for k in ('f_a', 'f_w', 'f_n', 'nif', 'LW_cal', 'LT_cal', 'fill_cal'):
        v = []
        for r in rows:
            try:
                v.append(float(r[k]))
            except (ValueError, KeyError):
                v.append(np.nan)
        out[k] = np.array(v)
    out['step'] = np.arange(len(rows)) * 4.0
    return out


print('=' * 96)
for d in sys.argv[1:] or ['_exp/lath192_ns4', '_exp/mid192_ns4']:
    S = load(d)
    print('\n### %s' % d)
    if S is None:
        print('   （无 series.csv）'); continue
    st, fa, fw, fn = S['step'], S['f_a'], S['f_w'], S['f_n']
    print('   %6s %8s %8s %8s %8s' % ('step', 'f_a(%)', 'f_w(%)', 'f_n(%)', '界面胞'))
    for k in range(min(len(st), 14)):
        print('   %6.0f %8.2f %8.2f %8.2f %8d'
              % (st[k], 100 * fa[k], 100 * fw[k], 100 * fn[k], int(S['nif'][k])))
    # 衰减判据
    j = np.where(np.isfinite(fa))[0]
    if j.size >= 4:
        f0 = fa[j[0]]
        # 首次降到 f0/3 的 step
        below = np.where(fa[j] <= f0 / 3.0)[0]
        if below.size:
            k3 = j[below[0]]
            print('   ⇒ `f_a` 从 %.2f%% 掉到 1/3（%.2f%%）用了 **%.0f 步**'
                  % (100 * f0, 100 * f0 / 3, st[k3] - st[j[0]]))
            print('   ⇒ 判定：%s'
                  % ('**H-1 数值圆化主导**（≤5 步）' if st[k3] - st[j[0]] <= 5
                     else '**H-2 动力学圆化主导**（缓慢衰减）'))
        else:
            print('   ⇒ `f_a` 在 %d 步内**没有**掉到 1/3（末值 %.2f%%）'
                  % (len(st), 100 * fa[-1]))
    print('   末态：f_a=%.2f%%  f_w=%.2f%%  f_n=%.2f%%（宽面/侧面应当保持）'
          % (100 * fa[-1], 100 * fw[-1], 100 * fn[-1]))
print('=' * 96)
print('★ 若 H-1 主导 ⇒ 想拿到平端面必须**减少平流的数值扩散**（换格式/加密 Δx），')
print('  而不是调 `M(n)`；若 H-2 主导 ⇒ 要动的是**界面能各向异性/尖点**（Wulff 造面）。')
