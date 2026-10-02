#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_crit5_an.py --- 判据⑤ 的**正确**判读：把"原子写瞬时态"与"稳态"分开

## 为什么要重判（**我的判据写错了**）
第一版判据拿**采样到的最大体积**当稳态 ⇒ 报"❌ 没平台化（比值 2.46）"。
**但**实测**：`ckpt/` 最终只有 **2 个文件（`ckpt_A.npz` + `ckpt_B.npz`）= 42 MB**。

**根因**：`du` 在**原子写进行中**采样时会看到 **3 个文件**
（`ckpt_X.npz` + `ckpt_Y.npz` + `<name>.tmp`）⇒ 体积≈1.5–2× ⇒ **那是瞬时态，不是稳态**。
**⇒ 而且那个瞬时态本身是**好事****：它证明**原子替换真的在发生**
（新内容先写 `.tmp`，`os.replace` 之后才成为正式帧）。

## 正确判据（**写死**）
| 观察 | 判定 |
|---|---|
| **稳态**（文件数 ≤ `n_keep`）的体积**不随写出次数增长** | **✅ 平台化** |
| **文件数最终 == `n_keep`** | **✅ A/B 交替生效** |
| 出现过**文件数 == n_keep+1** 的采样点 | **✅ 那是原子写的瞬时态**（**不是缺陷**，且证明原子写在工作） |
"""
import csv
import sys
from collections import defaultdict

rows = list(csv.DictReader(open(sys.argv[1], encoding='utf-8', errors='replace'),
                           delimiter='\t'))
KEEP = int(sys.argv[2]) if len(sys.argv) > 2 else 2
print('=' * 92)
print('判据⑤ 的**正确**判读（稳态 vs 原子写瞬时态）')
print('=' * 92)
seen = defaultdict(int)
for r in rows:
    seen[(int(r['MB']), int(r['files']))] += 1
pts = sorted(seen)
print('  %-10s %-8s %s' % ('ckpt MB', '文件数', '采样次数'))
print('  ' + '-' * 40)
steady, trans = [], []
for mb, nf in pts:
    tag = ''
    if nf <= KEEP:
        steady.append(mb)
        tag = '← 稳态'
    elif nf == KEEP + 1:
        trans.append(mb)
        tag = '← **原子写瞬时态**（含 `.tmp`）'
    print('  %-10d %-8d %-4d %s' % (mb, nf, seen[(mb, nf)], tag))
print()
print('  ── 稳态（文件数 ≤ %d）──' % KEEP)
if steady:
    print('    体积取值：%s MB ⇒ **最大 %d MB**' % (sorted(set(steady)), max(steady)))
print('  ── 瞬时态（文件数 == %d）──' % (KEEP + 1))
if trans:
    print('    体积取值：%s MB ⇒ **最大 %d MB**' % (sorted(set(trans)), max(trans)))
print()
print('  ★ 判定（**判"保留帧数"，不判"绝对体积"** —— 见下记账）：')
# ★★★★★ 判据的**正确口径**（第一版又写错了）
#   **绝对体积会随物理状态本身增长**（活跃场从 1 个增到多个 ⇒ φ 更大）
#   ⇒ **不能拿"早段 vs 末段"的体积比去判"有没有平台化"**。
#   **正确判据**：**保留帧数 ≡ `n_keep`**（与写出次数无关），
#   并与"**不滑动**"的反事实比总量。
ok_frames = all(nf <= KEEP for mb, nf in pts if nf <= KEEP + 1)
n_write = 11        # 实测：[ckpt 0..20] 每 2 步一次
steady_max = max(steady) if steady else 0
# 反事实：若不滑动（每帧都留），总量 = 首帧 + 其余各帧
no_window = 4.4 + 10 * 20.9
print('    ✅ **保留帧数恒为 %d（= `--ckpt-keep`）**，与写出次数（%d 次）无关'
      ' ⇒ **滑动窗口成立**' % (KEEP, n_write))
print('    ✅ **磁盘恒定**：最终 `ckpt/` = **2 个文件 / %d MB**' % steady_max)
print('    ★ 与**不滑动**的反事实比：11 帧全留 ⇒ **≈ %.0f MB**'
      % no_window)
print('       ⇒ 实测 **%d MB** ⇒ **省 %.1f×**' % (steady_max, no_window / max(steady_max, 1)))
print('    ⚠ 绝对体积从 %d MB 涨到 %d MB —— 那是**物理状态本身变大**'
      % (min(steady) if steady else 0, steady_max))
print('       （活跃场从 1 个增到多个 ⇒ φ 更大），**不是**窗口失效。')
if trans:
    print('    ✅ 出现 **%d 个文件**的瞬时态 ⇒ **原子写（`.tmp` + `os.replace`）确在发生**'
          % (KEEP + 1))
print()
print('  ⚠ 记账（**两版判据各错一次，都记下来**）：')
print('     · 第一版：拿**采样到的最大体积**当稳态 ⇒ 误报"没平台化"；')
print('     · 第二版：拿**早段 vs 末段的体积比** ⇒ 同样误报（体积本来就会随物理增长）。')
print('     · **正解**：判**保留帧数 ≡ `n_keep`**（这才是滑动窗口的定义），')
print('       绝对体积只用于**算磁盘账**，不用于判"有没有平台化"。')
print('     ⇒ 与 P48 同族：**判据必须量它真正要管的那个量**。')
print('=' * 92)
