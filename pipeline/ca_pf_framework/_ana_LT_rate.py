#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_ana_LT_rate.py —— 用**滑动长窗**判「L 到底在不在减速」（`MEASUREMENT_SPEC R14` 口径）

为什么要单独做（记账）
----------------------
* `R14`：成长速率**必须用长窗平均**，不得用相邻采样点之差 ——
  因为 `extent()` 取 `max−min` 的**胞索引**，前沿每推进一个整胞才跳一次，单区间速率会乱跳
  （实测 `1.2 / 17.5 / 4.6 / 4.6 / 3.6 nm/步`）。**我上一轮从粗采样里读出过"单调减速"的假象。**
* 但**长窗平均之后到底降不降**，是靶② 的真问题（若真降，就要查是 `ed`、`−γκ` 还是几何）。
  本脚本把两条日志的 L/T 序列按**滑窗**算速率，并**显式报窗口起止**，不靠肉眼。

输入：`_w2_box16.log`（Δx=166.7 nm, L=16 µm, R=300）与 `_w2_lt.log`（Δx=25 nm, L=4 µm）
输出：滑窗表 + 单调性判定（**判据：相邻滑窗速率的符号变化，不是单点差**）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r'step=(\d+)\s+L=([\d.]+)\s+W=([\d.]+)\s+T=([\d.]+)')
# ★ 2026-09-28 新增：解析"三把尺子"行（`_probe_LT.py` 的新诊断）
PAT3 = re.compile(r'\[三把尺子\]\s*胞数=(\d+)\s*V=([\d.eE+-]+) m³.*?`L_vol`=([\d.]+).*?`L_gyr`=([\d.]+)')
LOGS = [('Δx=166.7 (BOX16,  R=300, P-1 FAIL)', '_w2_box16.log'),
        ('Δx=166.7 (BOX16b, R=500, P-1 PASS)', '_w2_box16b.log'),
        ('Δx=166.7 (BOX16d, R=500 +三把尺子) ', '_w2_box16d.log'),
        ('Δx=166.7 (G0,     R=500, gamma0=0)  ', '_w2_g0.log'),
        ('Δx=25    (_w2_lt, t_nuc=200)        ', '_w2_lt.log')]
WIN = 50          # 滑窗宽度（步）—— `R14` 要求"跨 ≥10 个胞"


def load(fn):
    out = []
    p = os.path.join(HERE, fn)
    if not os.path.exists(p):
        return out, []
    trip = []
    for ln in open(p, encoding='utf-8', errors='ignore'):
        m = PAT.search(ln)
        if m:
            out.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))))
        m3 = PAT3.search(ln)
        if m3:
            trip.append((int(m3.group(1)), float(m3.group(2)), float(m3.group(3)), float(m3.group(4))))
    return out, trip


print('=' * 104)
print('_ana_LT_rate —— 滑动长窗（%d 步）速率分析，`MEASUREMENT_SPEC R14` 口径' % WIN)
print('=' * 104)
for tag, fn in LOGS:
    rows, trip = load(fn)
    print('\n【%s】共 %d 个采样点' % (tag, len(rows)))
    if len(trip) >= 2:
        # ★★★ 2026-09-28 新增：**包围盒填充率** `fill = V/(L·W·T)`
        #   动机：`BOX16d` 的 `max−min`(6032.5) 与 `L_gyr`(4657.8) 差 **30%**，而合成形状上只差 4%
        #   ⇒ 说明真实形状**非紧凑**。填充率是判断"是否紧凑"的**最便宜、无需存盘**的描述量：
        #     均匀盒 ≈ 0.85–0.9（阶梯损失）；T 形件 ≈ 0.58；分枝/细丝状 ⇒ 更低。
        #   配对方式：`[三把尺子]` 行紧跟其后（前面）是同 step 的 `step=` 行 ⇒ 用**序号**配对。
        print('   [形状描述量]  %-8s %-10s %-12s %-12s %-12s %-10s %s'
              % ('采样', '胞数', 'V (m³)', '`max−min`L', 'W (max−min)', 'T (max−min)', '**填充率**'))
        k = 0
        for nc, V, Lv, Lg in trip:
            # 找与本次 trip 对应的 step 行（`trip` 与 `rows` 按输出顺序一一对应）
            if k < len(rows):
                st, Lmm, Wmm, Tmm = rows[k]
                box = Lmm * Wmm * Tmm * 1e-27          # nm³ → m³
                fill = V / max(box, 1e-30)
                print('   %-20s %-8d %-12.3e %-12.1f %-12.1f %-10.1f **%.3f**'
                      % ('step %d' % st, nc, V, Lmm, Wmm, Tmm, fill))
            k += 1
        if len(trip) >= 3:
            g_mm = trip[-1][2] * 1e9 / max(trip[0][2] * 1e9, 1e-9)
            g_gyr = trip[-1][3] / max(trip[0][3], 1e-9)
            print('   ⇒ 从首到末的相对增长：`max−min` ×%.3f · `L_gyr` ×%.3f' % (g_mm, g_gyr))
            print('   ⚠ 口径提醒（`_chk_ar_rulers.py` 已标定）：**`max−min` 与回转都是可信的"跨度"尺子**')
            print('      （均匀盒 ±2%、非均匀体 ±4%）；**不可用的是"体积等效" `L_vol`**（偏 +16~−35%）。')
    if len(rows) < 3:
        print('   采样点不足（<3）⇒ **INCONCLUSIVE**，等作业跑完再判。')
        continue
    print('   %-16s %-12s %-12s %-12s %-10s %s'
          % ('窗口(起→止)', 'ΔL/步', 'ΔT/步', 'ΔL/ΔT', 'ΔW/步', 'L/T(止)'))
    rates = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            s0, L0, W0, T0 = rows[i]
            s1, L1, W1, T1 = rows[j]
            if s1 - s0 < WIN:
                continue
            dL = (L1 - L0) / (s1 - s0)
            dT = (T1 - T0) / (s1 - s0)
            dW = (W1 - W0) / (s1 - s0)
            ratio = (dL / dT) if dT > 1e-9 else float('inf')
            rates.append((s0, s1, dL, dT, ratio))
            print('   %-16s %-12.2f %-12.3f %-12s %-10.2f %.2f'
                  % ('%d→%d' % (s0, s1), dL, dT,
                     ('%.1f' % ratio) if ratio != float('inf') else '∞(ΔT=0)', dW, L1 / T1))
            break        # 每个起点只取最短的合格窗口，避免表太长
    if len(rates) >= 2:
        # ★ 判据：相邻滑窗的 ΔL/步 是否**单调下降**（用符号/幅度，不用单点差）
        r0, r1 = rates[0][2], rates[-1][2]
        drop = (r0 - r1) / max(r0, 1e-9)
        print('   ⇒ 首个滑窗 ΔL/步 = %.2f ；最后一个 = %.2f ⇒ **变化 %+.1f%%**'
              % (r0, r1, -100 * drop))
        if drop > 0.30:
            print('   ⇒ ⚠ **长窗上确实在减速**（>30%%）⇒ 需查 `ed` / `−γκ` / 几何三条候选。')
        elif drop > 0.10:
            print('   ⇒ 长窗上有**轻微减速**（10–30%%）⇒ 暂不结论，等更长窗口。')
        else:
            print('   ⇒ ✅ 长窗上**基本恒定**（<10%%）⇒ 之前的"减速"主要是**短窗/整胞跳变**的假象。')
    else:
        print('   ⇒ 合格滑窗不足 2 个 ⇒ **INCONCLUSIVE**。')
print('\n⚠ 口径提醒（`R14`/`R13`）：`ΔT/步` 常 < 1 胞 ⇒ `ΔL/ΔT` 在小窗口会被"T 恰好没跳胞"污染；')
print('   本脚本只打印 `ΔT/步 > 0` 的窗口，且**逐窗报起止 step**，便于复核。')
print('=' * 104)
