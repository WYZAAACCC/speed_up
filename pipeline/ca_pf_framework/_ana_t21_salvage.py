#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_ana_t21_salvage.py —— 从 `_w2_t21.log` 的**轨迹行**重建 `AR@f_ref`（抢救被终止的 β 扫描）

背景（为什么要抢救）
--------------------
`T21` 的 per-β 汇总表（`β_h β_w f_end AR@f_ref 夹逼 判定`）**只在四档全部跑完时才打印**，
而我在 Round 126 终止了它（原因：`--f-target 0.05` 是判据插值点 `f=0.002` 的 **25 倍**，
实测还需 ~5 h，严重阻塞引擎冻结）。
但 **`[轨迹 β=X] step=.. f=.. AR=..` 逐行都在日志里** ⇒ 判据本身就是"在 `f=0.002` 上插值"
⇒ **可以自己重建**，不必重跑。

判据（与 `T21` 原判据一致）
--------------------------
* 在 `f_ref` 上对每个 β 档的 `(f, AR)` 轨迹**线性插值** ⇒ `AR@f_ref`；
* 报**夹逼区间**（插值所跨的两个采样点）—— 若 `f_ref` 落在轨迹之外，必须报 **INCONCLUSIVE**，
  **不得**外推（`MEASUREMENT_SPEC R8`/教训：夹逼不到就标 INCONCLUSIVE）。

⚠ 记账：本脚本**只读日志**，不重跑、不改引擎。它是**抢救**，不是替代 ——
  正式读数仍应在 `doublet` 落地后用**单批** Wave 2 重取。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, '_w2_t21.log')
PAT = re.compile(r'\[轨迹 β=([\d.]+)\]\s*step=(\d+)\s+f=([\d.]+)\s+AR=([\d.]+)')
F_REF = 0.002          # 与 T21 的判据一致（日志第 36 行）

data = {}
if os.path.exists(LOG):
    for ln in open(LOG, encoding='utf-8', errors='ignore'):
        m = PAT.search(ln)
        if m:
            b = float(m.group(1))
            data.setdefault(b, []).append((float(m.group(3)), float(m.group(4)), int(m.group(2))))

print('=' * 100)
print('_ana_t21_salvage —— 从轨迹行重建 `AR@f_ref=%.3f`（抢救被终止的 β 扫描）' % F_REF)
print('=' * 100)
if not data:
    print('   ⛔ 日志里没有轨迹行 ⇒ 无法抢救。')
    sys.exit(1)

print('\n   %-8s %-10s %-12s %-22s %s' % ('β_h', 'f_end', 'AR(f_end)', '夹逼区间(f)', 'AR@f_ref'))
rows = []
for b in sorted(data):
    tr = sorted(data[b])                       # 按 f 升序
    f_end, ar_end, _ = tr[-1]
    ar_ref, bracket, ok = None, None, False
    for i in range(len(tr) - 1):
        f0, a0, s0 = tr[i]
        f1, a1, s1 = tr[i + 1]
        if f0 <= F_REF <= f1 and f1 > f0:
            ar_ref = a0 + (a1 - a0) * (F_REF - f0) / (f1 - f0)
            bracket = (f0, f1)
            ok = True
            break
    rows.append((b, f_end, ar_end, ar_ref, bracket, ok))
    print('   %-8.2f %-10.5f %-12.3f %-22s %s'
          % (b, f_end, ar_end,
             ('%.5f–%.5f' % bracket) if bracket else '（未跨 f_ref）',
             ('%.3f' % ar_ref) if ok else '**INCONCLUSIVE**'))

good = [r for r in rows if r[5]]
print('\n   可比档数 = **%d / %d**' % (len(good), len(rows)))
if len(good) >= 2:
    ars = [r[3] for r in good]
    bs = [r[0] for r in good]
    print('   β_h = %s' % '  '.join('%.2f' % x for x in bs))
    print('   AR@f_ref = %s' % '  '.join('%.3f' % x for x in ars))
    lo, hi = min(ars), max(ars)
    _ratio = (max(bs) / min(bs)) if min(bs) > 1e-12 else float('inf')
    print('   ⇒ β 区间 = %s（β_h=0 时比值无定义 ⇒ 不报倍数，只报端点）'
          % ('%.2f–%.2f' % (min(bs), max(bs))))
    print('   ⇒ AR 从 %.3f 变到 %.3f（极差 **%.3f**）' % (lo, hi, hi - lo))
    if (hi - lo) < 0.15:
        print('   ⇒ ★ **`AR@f_ref` 对 β 几乎无分辨力**（极差 < 0.15）⇒ 与 **B3「文献 2D AR 不能标定 β」一致**。')
        print('      ⚠ 但 B3 的原始结论是在**各向异性被压缩 ~4 倍**的条件下得到的；')
        print('        本次是 `norm_smooth=2` + A-1 修复**之后**的读数 ⇒ **可以作为 B3 的重做证据**。')
    else:
        print('   ⇒ AR 对 β 有可分辨的依赖（极差 ≥ 0.15）⇒ **B3 需要重新表述**。')
else:
    print('   ⇒ 可比档数不足 ⇒ **INCONCLUSIVE**。')
print('\n   ⚠ 记账：本表是**抢救读数**（从被终止的跑里重建），')
print('     **不得**当作最终判据 —— 正式读数应在 `doublet` 落地后用**单批** Wave 2 重取。')
print('=' * 100)
