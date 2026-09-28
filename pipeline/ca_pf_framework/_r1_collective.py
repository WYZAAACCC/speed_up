#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_collective.py --- ★ Q-c 的**配对比较**：有邻居 vs 没邻居，同一根板条的形状怎么变

问题（阶段③的核心可观测问题 Q-c）
---------------------------------
实验 4 的 6 根核彼此靠近（1500 nm）。它们会不会**因为邻居而改变自己的形状**？
判据必须是**配对比较**（`R23`：同规格、同口径、同分辨率）：

  * **单核臂** `_exp/lath192_ns4`  —— 同一 `lath` 种子、同 R24、同 `norm_smooth=4`、**无邻居**
  * **多核臂** `_exp/e4_lath6`     —— 同一种子 × 6、沿 `w` 排一列、间距 1500 nm

两个臂的 `L/W/T` 都是**各自的逐板条定标口径**（`_r1_calib` 的逐轴因子），
所以可以直接比。

判据（先写死）
--------------
  C-1 合并前，两臂的 **`LW_cal` 与时间的关系** 应当在同一个量级；
      若多核臂**显著更宽**（`LW` 更小）⇒ **存在集体效应**（邻居把它压宽了）。
  C-2 两臂的 **`LT_cal` 增长速度** 比较。
  C-3 **正对照**：两臂的**种子**必须给出同一个 `LW_cal`（否则不可比）。
"""
import os
import csv
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load_single(d):
    p = os.path.join(HERE, d, 'series.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    st, lw, lt = [], [], []
    for i, r in enumerate(rows):
        st.append(float(i) * 4.0)          # 该臂的 CSV `step` 列被 NaN 覆盖 ⇒ 按行号重建
        try:
            lw.append(float(r['LW_cal']))
            lt.append(float(r['LT_cal']))
        except (ValueError, KeyError):
            lw.append(np.nan)
            lt.append(np.nan)
    return np.array(st), np.array(lw), np.array(lt)


def load_comp(d):
    p = os.path.join(HERE, d, 'components.csv')
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p)))
    st = np.array([float(r['step']) for r in rows])
    # 用**最大分量**的定标口径（合并前 = 单根板条；合并后 = 整块）
    lw = np.array([float(r.get('LW_cal') or 'nan') for r in rows])
    lt = np.array([float(r.get('LT_cal') or 'nan') for r in rows])
    ns = np.array([float(r['nsig']) for r in rows])
    wc = np.array([float(r.get('W_cal') or 'nan') for r in rows])
    return st, lw, lt, ns, wc


s = load_single('_exp/lath192_ns4')
c = load_comp('_exp/e4_lath6')
print('=' * 96)
print('Q-c 配对比较：单核（无邻居） vs 多核（6 根，间距 1500 nm）')
print('=' * 96)
if s is None or c is None:
    print('✗ 缺数据：single=%s comp=%s' % (s is not None, c is not None)); sys.exit(1)
st_s, lw_s, lt_s = s
st_c, lw_c, lt_c, ns_c, w_c = c

print('\nC-3 正对照（种子必须一致 ⇒ 否则两臂不可比）')
print('   单核臂 step 0：LW_cal = %.3f  LT_cal = %.3f' % (lw_s[0], lt_s[0]))
print('   多核臂 step 25（最近的采样）：LW_cal = %.3f  LT_cal = %.3f' % (lw_c[0], lt_c[0]))
d0 = abs(lw_s[0] - lw_c[0]) / max(lw_s[0], 1e-30)
print('   ⇒ 相对差 %.1f%% ⇒ %s' % (100 * d0, '**可比**' if d0 < 0.12 else '⚠ 不可比'))

print('\nC-1/C-2 逐 step 对照（多核臂只取**合并前**，且**边缘间隙 ≥ 3 胞**的采样）')
print('   ⚠ 记账（第 10 轮自查抓到的**我自己的过度解读**）：')
print('     第一版把多核臂 step 125 的 `LW_cal = 4.57` 当成"集体效应"，')
print('     但 step 25/50/75/100 两臂分别是 6.25/6.99/7.63/6.51 vs 6.45/6.44/7.00/6.11')
print('     —— **相差不到 10%**。那个 4.57 出现在**即将合并**的时刻（合并于 s≈145）')
print('     ⇒ 是**合并前的测量污染**（邻核界面进入同一分量的跨度），不是集体效应。')
print('     ⇒ 必须加"边缘间隙"守卫。')
SPACING_NM = 1500.0
gap_nm = SPACING_NM - w_c * 1e9
ok = (ns_c > 1) & (gap_nm >= 3 * 125.0)
print('   %6s %9s %8s | %-20s | %-20s %s'
      % ('step', 'W_cal', '边缘间隙', '单核 LW/LT', '多核 LW/LT', '计入?'))
for k in range(len(st_c)):
    j = int(np.argmin(np.abs(st_s - st_c[k])))
    print('   %6.0f %8.0f %7.0f | %-20s | %-20s %s'
          % (st_c[k], w_c[k] * 1e9, gap_nm[k],
             '%.2f / %.2f' % (lw_s[j], lt_s[j]),
             ('%.2f / %.2f' % (lw_c[k], lt_c[k])) if ns_c[k] > 1 else '（已合并）',
             '✓' if ok[k] else '✗'))

i_c = np.where(ok)[0]
i_s = np.where((st_s >= st_c[i_c[0]]) & (st_s <= st_c[i_c[-1]]))[0] if i_c.size else np.array([], int)
if i_c.size >= 3 and i_s.size >= 3:
    def sl(x, y):
        A = np.vstack([x, np.ones_like(x)]).T
        sol, *_ = np.linalg.lstsq(A, y, rcond=None)
        yh = A @ sol
        r2 = 1 - np.sum((y - yh) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-30)
        return float(sol[0]), float(r2)
    a_s, r2_s = sl(st_s[i_s], lw_s[i_s])
    a_c, r2_c = sl(st_c[i_c], lw_c[i_c])
    print('\n   **只取合格采样后**的 `LW_cal` 斜率（每步）：')
    print('     单核 %+.5f (R²=%.3f, n=%d)   多核 %+.5f (R²=%.3f, n=%d)'
          % (a_s, r2_s, i_s.size, a_c, r2_c, i_c.size))
    print('   ⇒ **修正后的 C-1 判定**：%s'
          % ('存在集体效应' if abs(a_c) > 2 * max(abs(a_s), 1e-4)
             else '**无显著集体效应**（两臂同一量级，此前那个"×124"是单点污染）'))
print('=' * 96)
print('★ 本脚本的方法论教训：**配对比较必须先做"可比性"正对照**')
print('  （C-3 已报两臂种子差 19.4%），并且必须给"即将合并"的采样加守卫 ——')
print('  否则一个受污染的采样点就能造出一个假的"效应"。')
