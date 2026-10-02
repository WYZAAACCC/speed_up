#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_memfit.py --- 用 `_r581_nvscale.py` 的**实测峰值 RSS** 反解内存定律，并判决 nv=540。

## 为什么要重做这件事
`R550_MEMORY_ENVELOPE.md` 的内存定律（以及 `R580` 在 N=160 上的复测）给的是
`M = a·nv·N³/2²⁰ + c·N³/2²⁰`，其中 `onfly+f32` 档 `a=5.0`、`c=388`。
按它算 **N=160/nv=540 ⇒ 12.1 GB ⇒ 可行**。
但 `_r581_nvscale.py` 的**独立看门狗实测 `VmHWM`** 给出：

| N | nv | 实测峰值 RSS |
|---|---|---|
| 64 | 24 | 513.5 MB |
| 64 | 72 | 778.3 MB |
| 64 | 144 | 1131.9 MB |
| 64 | 288 | 1829.3 MB |
| 64 | 540 | 3100.3 MB |
| 160 | 24 | **5087.9 MB** |
| 160 | 72 | **8606.3 MB** |

N=160/nv=24 实测 **5087.9 MB**，而 R550 定律给 1984 MB ⇒ **定律低报 2.6×**。
⇒ 必须用**本轮的实测**反解，并**外推判决**。

## 本脚本做什么
1. 最小二乘拟合 `M = a·(nv·CELL) + c·CELL + d`（三项，含 N 无关常数 `d`）；
2. 分别用 N=64 系列 / N=160 系列 / 全体系列拟合，**报出三组**（不挑好看的）；
3. 用每组预测 `N=160/nv=540`，与 **22 GB 预算**对比 ⇒ 判决；
4. 同样预测 `N=160/nv=72`（备选）并判决；
5. 打印 **R550 旧定律 vs 本轮实测** 的对照（**记账，不掩盖**）。
"""
import numpy as np

# (N, nv, 峰值 RSS MB) —— 来自 `_w2_r581_nvscale.log`（独立看门狗读 /proc/<pid>/status 的 VmHWM）
DATA = [(64, 24, 513.5), (64, 72, 778.3), (64, 144, 1131.9),
        (64, 288, 1829.3), (64, 540, 3100.3),
        (160, 24, 5087.9), (160, 72, 8606.3)]
BUDGET_MB = 22528.0          # WSL 24 GB 上限，AGENTS §1.3 说按 22 GB 规划
PLAN_MB = 22000.0


def cell(N):
    return N ** 3 / 2.0 ** 20


def fit(rows, label):
    """最小二乘解 M = a*(nv*CELL) + c*CELL + d。"""
    A = np.array([[nv * cell(N), cell(N), 1.0] for N, nv, _ in rows])
    b = np.array([m for _, _, m in rows])
    sol, res, rank, sv = np.linalg.lstsq(A, b, rcond=None)
    pred = A @ sol
    err = np.abs(pred - b) / b
    return dict(label=label, a=sol[0], c=sol[1], d=sol[2],
                max_rel_err=float(err.max()), n=len(rows), coef=sol)


def predict(f, N, nv):
    return f['a'] * nv * cell(N) + f['c'] * cell(N) + f['d']


def old_law(N, nv):
    """R550/R580 的两项定律（onfly+f32：a=5.0, c=388）。"""
    return 5.0 * nv * cell(N) + 388.0 * cell(N)


L = ['=' * 96,
     'R581 —— 内存定律的**实测反解** + `nv=540` 的可行性判决',
     '=' * 96,
     '  数据源：_r581_nvscale.py 的独立看门狗（VmHWM）',
     f'  预算：WSL 上限 {BUDGET_MB/1024:.1f} GB；规划口径 **{PLAN_MB/1024:.1f} GB**（AGENTS §1.3）',
     '']
L.append('  %-6s %-6s %-12s %-12s %s' % ('N', 'nv', '实测峰值MB', 'R550旧定律MB', '旧/实'))
L.append('  ' + '-' * 60)
for N, nv, m in DATA:
    o = old_law(N, nv)
    L.append('  %-6d %-6d %-12.1f %-12.1f %.2f×'
             % (N, nv, m, o, o / m))
L.append('')

fits = []
fits.append(fit([r for r in DATA if r[0] == 64], 'N=64 系列（5 点）'))
fits.append(fit([r for r in DATA if r[0] == 160], 'N=160 系列（2 点）'))
fits.append(fit(DATA, '全体（7 点）'))
L.append('  ── 拟合 M = a·(nv·CELL) + c·CELL + d ──')
for f in fits:
    L.append('    %-16s  a=%8.3f  c=%9.1f  d=%9.1f   最大相对残差=%.2f%%  (n=%d)'
             % (f['label'], f['a'], f['c'], f['d'],
                100 * f['max_rel_err'], f['n']))
L.append('')
L.append('  ⚠ 记账：R550/R580 的 `a=5.0` 与本轮反解的 a≈19–21 **差约 4 倍**。'
         '两者口径不同')
L.append('     （旧定律拟合的是"常驻数组"，本轮 VmHWM 是**含全部临时量的峰值**）。'
         '**判据取峰值** —— 因为 OOM 看的是峰值。')
L.append('')

L.append('=' * 96)
L.append('★ 判决')
L.append('=' * 96)
L.append('  %-22s %-14s %-12s %s' % ('配置', '预测峰值MB', '=GB', '判决（≤22 GB）'))
L.append('  ' + '-' * 74)
verdict = {}
for N, nv in ((160, 540), (160, 288), (160, 144), (160, 72), (160, 48), (160, 24)):
    vals = [predict(f, N, nv) for f in fits]
    lo, hi = min(vals), max(vals)
    ok = hi <= PLAN_MB
    verdict[(N, nv)] = (lo, hi, ok)
    L.append('  N=%-4d nv=%-4d        %-14s %-12s %s'
             % (N, nv, '%.0f – %.0f' % (lo, hi), '%.1f – %.1f' % (lo / 1024, hi / 1024),
                '✅ 可行' if ok else '❌ **超预算**（最高 %.1f GB）' % (hi / 1024)))
L.append('')
v540 = verdict[(160, 540)]
if not v540[2]:
    L.append('  ⇒ ★★ **`nv=540` 在 N=160 上不可行**（预测 %.1f–%.1f GB ≫ %.1f GB）。'
             % (v540[0] / 1024, v540[1] / 1024, PLAN_MB / 1024))
    L.append('     这不是"优化不够"，是**墙**：WSL 24 GB 硬上限，加大只会 OOM/整机卡死（AGENTS §3.12）。')
    L.append('     而且 `nv=540` 的**出处本身已被推翻**：`R525 §6` 按 `B≈90`（来自 `R507`）算 `B·n=540`，')
    L.append('     但 **`R525 §4b` 自己的 B 扫描把 B 降到 3–5（B=3 是 5/5 全过）**')
    L.append('     ⇒ 物理给出的总根数是 `B·n = 18–30` ⇒ `nv = 12×m, m ≥ ceil(30/12)=3` 就够表示。')
    L.append('     ⇒ **建议生产配置改为 `nv=72`（=12×6，对 18–30 根留 2.4–4 倍余量）**：')
    v72 = verdict[(160, 72)]
    L.append('       预测峰值 %.1f–%.1f GB ⇒ %s；实测（本轮）**8.6 GB**、**11.97 s/步**'
             % (v72[0] / 1024, v72[1] / 1024, '✅ 可行' if v72[2] else '❌'))
    L.append('       ⇒ 600 步 ≈ **%.1f h**（按实测 11.97 s/步）'
             % (11.965 * 600 / 3600.0))
    L.append('')
    L.append('  ⚠ **C5（块填满盒子）不会因为 nv=72 而变差** —— 它现在被**超临界位点数（3–5）**卡住，')
    L.append('     不是被 nv 卡住（`R525 §4b` 结论 3 已实测：抬 nv 对拒绝率无效）。')
    L.append('     ⇒ 这条要进 **待用户确认清单**（改的是"容量"，不是"物理"）。')
out = '\n'.join(L)
print(out)
open('_w2_r581_memfit.log', 'w').write(out + '\n')
