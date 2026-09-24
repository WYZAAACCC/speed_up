#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''_ti64_stats.py --- 从日志解析 20 种子结果，做统计检验并写报告'''
import re, numpy as np
from scipy import stats
txt = open('/mnt/f/speed_up/_ti64_cmp.log', encoding='utf-8').read()
def grab(tag):
    rows = []
    for m in re.finditer(tag + r'\s+seed\s+\d+: 晶粒\s+(\d+), 形核 (\d+), 形核占比 ([\d.]+), 平均 ([\d.]+) 胞, 基底加权 min∠ ([\d.]+)', txt):
        rows.append([float(x) for x in m.groups()])
    return np.array(rows)
E = grab('ExaCA'); M = grab('我方')
names = ['晶粒数', '形核数', '形核占比', '平均晶粒(胞)', '基底加权 min∠(°)']
print('%-18s %-20s %-20s %-10s %s' % ('指标', 'ExaCA (n=%d)' % len(E), '我方 (n=%d)' % len(M), '相对差', 'Welch p'))
for i, nm in enumerate(names):
    a, b = E[:, i], M[:, i]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    print('%-18s %-20s %-20s %+9.1f%%  p=%.3g' % (
        nm, '%.3f ± %.3f' % (a.mean(), a.std(ddof=1)), '%.3f ± %.3f' % (b.mean(), b.std(ddof=1)),
        100 * (b.mean() - a.mean()) / a.mean(), p))
tot_e = E[:, 0].mean() * E[:, 3].mean(); tot_m = M[:, 0].mean() * M[:, 3].mean()
print()
print('固相总量估算: ExaCA %.0f 胞 / 我方 %.0f 胞 (域 = 8000) ⇒ ExaCA 剩 %.0f%% 未固' % (
    tot_e, tot_m, 100 * (1 - tot_e / 8000)))
open('/mnt/f/speed_up/bench/exaca/TI64_VS_MINE.md', 'w', encoding='utf-8').write(
"""# Ti64：ExaCA vs 我的 CA（同材料同初始条件，2026-09-24）

## 设置（两码逐点相同）
- 算例：ExaCA `Inp_SmallDirSolidification` 的其它参数不变（20³、dx=1µm、底面 25% 位点、
  形核 N=250×10¹²m⁻³ ⇒ 期望 2 个位点、dtn=5 K/σ=0.5 K），**只把材料换成 Ti64**；
- 热场（ExaCA 约定）：ΔT(z,t) = R·t − G·z_phys，G=5e5 K/m，**R=3e5 K/s（冷却速率）**；
  dt = 6.667e-8 s；ExaCA 跑到 2000 步（Ti64 的凝固区间短），我方同步 2000 步；
- **界面响应：两码共用同一张 LKT 表**（我给 ExaCA 加了 `"function":"table"`，读 `dT[K],V[m/s]`
  两列 CSV，按 dt/dx 归一 + 线性插值 + 端点截断）⇒ 零拟合误差。
- 各 20 个随机种子。

## 结果
见终端表格（指标 / ExaCA / 我方 / 相对差 / Welch p）。要点：
- **晶粒数差 1.8%**（p 不显著）✓
- 平均晶粒尺寸差 9%（我方偏大）⚠
- 形核晶粒占比差 −25%（我方偏低）⚠
- 基底尺寸加权 min∠ 差 +7.6%（我方择优略弱）⚠
- **固相总量**：我方 8007/8000（全固），ExaCA ~7200（还剩 ~10% 未固）
  ⇒ **我方前沿系统性略快**。

## 解释与下一步
四个残差同向：我方**前进略快、择优略弱、形核粒占比略低** —— 与"我把 ℓ 集总成整晶粒一个值
（用前沿 V 的 p90）"完全一致：集总会用最快那段前沿的速率推进整个晶粒 ⇒ 偏快、错取向抑制偏弱。
ExaCA 是**逐胞 ℓ + 每次捕获精确重定心**。
⇒ 下一步：把我的捕获改成同形态（`capture="cell"`），再重跑本对比；若四项都落进几 %，即按你的标准"可用"。
""")
print('已写 bench/exaca/TI64_VS_MINE.md')