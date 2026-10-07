#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""_r580_bisect_cmp.py --- 修正 NaN 处理后的**逐列**对照（只读盘上已有的 series.csv）。

## 为什么必须重写比较器（量具 bug 留档）
二分脚本第一版写的是
```python
if d != 0.0: rows.append((c, d))     # ← d 可能是 nan
```
而 `series.csv` 里有**合法的 NaN 列**（未定义/无界面时）。`nan != 0.0` 为真
⇒ **60 个 NaN 列全部被当成"有差异"**，真差异（`E_el_J`）被淹没。

⚠ 顺带发现**更严重的旧问题**：`_r578_smoke.sh` 与 `_r580_smoke_cli.sh` 的 C-3 用的是
```python
if d > worst: worst, wc = d, c    # ← nan > 0.0 恒为 False
```
⇒ **NaN 列被静默跳过**。也就是说它们报的"逐位一致"只对**双方都有限**的列成立 ——
本身不算错，但**必须显式说出来**，否则读者会以为"全部 96 列都逐位相同"。

## 本脚本的口径（写死，可复算）
对每个共有列：
* `both-nan`：两臂在该列**全为 NaN** ⇒ 不算差异，单独计数；
* `finite`：只保留**两臂都有限**的位置，算 `max|Δ| / max|ref|`；
* `nan-pattern`：两臂的 NaN **位置**不一致 ⇒ **单独报**（这是真差异，不能混进数值差）；
* 另报 `n_diff_finite`（有限位置上真有差异的列数）。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '_exp', '_bk_eng')
BASE = sys.argv[1] if len(sys.argv) > 1 else 'bis_base'
ARMS = (sys.argv[2].split(',') if len(sys.argv) > 2 else
        ['bis_eps0', 'bis_edp', 'bis_kloop', 'bis_act', 'bis_arg2',
         'bis_grad', 'bis_pfphi', 'bis_all'])


def rd(t):
    p = os.path.join(R, 'dry_' + t, 'series.csv')
    if not os.path.exists(p):
        return None, None
    with open(p) as fh:
        h = fh.readline().strip().split(',')
    return h, np.genfromtxt(p, delimiter=',', names=True)


def col(a, c):
    x = np.atleast_1d(np.asarray(a[c], dtype=float)).ravel()
    return x


h0, a0 = rd(BASE)
if a0 is None:
    print('  ❌ 缺 BASE：%s' % BASE)
    raise SystemExit(1)
n0 = len(col(a0, h0[0]))
print('  BASE = %s：%d 列 %d 行' % (BASE, len(h0), n0))
print()
print('  %-10s %-9s %-9s %-11s %-9s %s'
      % ('臂', '有限列', 'both-nan', 'nan位置不同', '真有差异', '差异列（相对差降序，最多 6 个）'))
print('  ' + '-' * 104)

for t in ARMS:
    h1, a1 = rd(t)
    if a1 is None:
        print('  %-10s (缺 series.csv)' % t)
        continue
    common = [c for c in h0 if c in h1 and c != 'wall_s']
    n_fin = n_bn = n_nanpat = 0
    diffs = []
    for c in common:
        x, y = col(a0, c), col(a1, c)
        m = min(len(x), len(y))
        if m == 0:
            continue
        x, y = x[:m], y[:m]
        fx, fy = np.isfinite(x), np.isfinite(y)
        if not fx.any() and not fy.any():
            n_bn += 1
            continue
        if not np.array_equal(fx, fy):
            n_nanpat += 1
        both = fx & fy
        if not both.any():
            continue
        n_fin += 1
        xb, yb = x[both], y[both]
        mx = float(np.max(np.abs(xb)))
        d = 0.0 if mx == 0.0 else float(np.max(np.abs(xb - yb))) / mx
        if d != 0.0:
            diffs.append((c, d))
    diffs.sort(key=lambda r: -r[1])
    names = ' '.join('%s=%.2e' % (c, d) for c, d in diffs[:6])
    if len(diffs) > 6:
        names += ' …共 %d 列' % len(diffs)
    if not names:
        names = '（无）'
    print('  %-10s %-9d %-9d %-11d %-9d %s'
          % (t, n_fin, n_bn, n_nanpat, len(diffs), names))

print()
print('  ★ 读数规则：')
print('    · 「真有差异」= 在两臂**都有限**的位置上 max|Δ|/max|ref| ≠ 0 的列数；')
print('    · 「both-nan」列两臂都是 NaN ⇒ **不算差异**（这是上一版比较器的坑）；')
print('    · 「nan位置不同」> 0 是**真差异**（NaN 出现的位置变了），必须单独交代；')
print('    · 只有 `bis_pfphi` 有差异 ⇒ 与其它开关无关；多个单独臂都有 ⇒ 各自补判据；')
print('      单独臂全 0 而 `bis_all` ≠ 0 ⇒ 是**交互**。')
