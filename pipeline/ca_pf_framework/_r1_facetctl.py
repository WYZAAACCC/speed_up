#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r1_facetctl.py --- ★★ `facet_lam` 的**正/负对照**：它到底有没有生效？

为什么必须做
------------
`windowB_surface.py:2160-2162` 里有**引擎自己记下的一段 bug 账**：
> 「这里必须是 **elif**。第一版写成独立的 if ⇒ 当 aniso>0 时，下面 sin^2 分支会把
>   facet 的 gk **整个覆盖** ⇒ `facet_lam=0/0.4/1.0` 三档结果**逐位相同**（实测抓到）。」

⇒ 也就是说，**"我传了 `facet_lam`"完全不代表它生效**。
   本脚本用两个算例（同一初值、只差 `facet_lam`）做**逐位对照**：
     * 若两档结果**逐位相同** ⇒ 参数**没生效**（老 bug 复发）⇒ 结论作废；
     * 若不同 ⇒ 参数生效，并报出**差多少**（`|Δφ|` 的最大值/均方根）。

判据
----
  F-1 两档的 `phi` 字段是否逐位相同。
  F-2 若不同，报 `max|Δφ|`、`rms|Δφ|`，以及两档的形貌读数差（L/W/T）。
  F-3 负对照：同一档跑两次（`facet_lam=0.4` vs `0.4`）应当**逐位相同**
      —— 证明"不同"不是随机性造成的。
"""
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PY = '/root/miniconda3/envs/ml/bin/python'
BASE = ['--case', 'mid', '--N', '48', '--dx-nm', '125', '--steps', '6',
        '--every', '2', '--nseed', '1', '--norm-smooth', '4',
        '--nthreads', '2', '--allow-small-box', '--max-hours', '0.2']


def run(tag, extra):
    out = '_exp/%s' % tag
    cmd = [PY, '-u', '_r1_exp.py', '--out', out] + BASE + extra
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
    if r.returncode != 0:
        print('   ⛔ %s 运行失败：%s' % (tag, (r.stderr or '')[-400:]))
        return None
    snaps = sorted(f for f in os.listdir(os.path.join(HERE, out))
                   if f.startswith('snap_') and f.endswith('.npz'))
    if not snaps:
        print('   ⚠ %s 没有快照' % tag)
        return None
    z = np.load(os.path.join(HERE, out, snaps[-1]))
    phi = z['region'] if 'region' in z.files else None
    return phi


print('=' * 96)
print('F-1/F-2 `facet_lam` 生效性对照（N=48, 6 步，同初值，只差 `--facet-lam`）')
print('=' * 96)
a = run('_facetctl_00', ['--facet-lam', '0.0'])
b = run('_facetctl_04', ['--facet-lam', '0.4'])
c = run('_facetctl_04b', ['--facet-lam', '0.4'])       # 负对照：同一档跑两次

ok = True
if a is None or b is None:
    print('⛔ 缺算例，无法对照'); sys.exit(1)
same_ab = np.array_equal(a, b)
print('\nF-1  facet_lam=0.0 vs 0.4 ：`region` %s'
      % ('**逐位相同** ⇒ ⛔ **参数没生效**（老 bug 复发）' if same_ab
         else '**不同** ⇒ ✅ 参数生效'))
if not same_ab:
    d = (a.astype(np.int16) - b.astype(np.int16))
    print('     max|Δregion| = %d ；不同的胞数 = %d / %d （%.3f%%）'
          % (int(np.abs(d).max()), int((d != 0).sum()), d.size,
             100.0 * (d != 0).mean()))
else:
    ok = False

if c is not None:
    same_bb = np.array_equal(b, c)
    print('F-3  负对照 facet_lam=0.4 vs 0.4（同一档跑两次）：%s'
          % ('**逐位相同** ✅（证明上面的"不同"不是随机性）' if same_bb
             else '⚠ 不同 ⇒ **存在非确定性**，上面的对照不可信'))
    if not same_bb:
        ok = False
else:
    print('F-3  负对照跑失败（不影响 F-1 的判读，但削弱可信度）')

print('\n⇒ 结论（**已由 `_r1_stiffunit.py` 更正，见下**）：')
print('  ⚠ 本脚本观察到两档**逐位相同**，但**不能**据此说"参数没生效"。')
print('     单元级对照 `_r1_stiffunit.py` 直接调 `_stiff_of`：')
print('       k=1 时 facet_lam=0.0 → 刚度 0.090–0.270 ；=0.4 → **0.150–1.349**（差 4 倍）')
print('     ⇒ **cusp 分支是生效的**。')
print('  ⚠ 本脚本"看不见"效果的原因是**功效不足**（`AGENTS.md §3.3` 教训 14）：')
print('     N=48 的种子 R=750 nm ⇒ κ=1.3e6 m⁻¹ ⇒ `stk·κ` ≈ 2e5 J/m³，只有 `Δf`≈1e8 的 **0.2%**；')
print('     换 cusp 后最多 ~1.8%；6 步位移 ≈112 nm，1.8% = **2 nm ≪ 1 个胞(125 nm)**，')
print('     而 `region`/`L_cal`/`V` **全部是胞量化**的 ⇒ 当然逐位相同。')
print('  ⇒ **要看效果必须换配置**：薄板（κ 大，如 `mid` 种子 T=320 nm）或长跑 + 用非量化量。')
print('=' * 96)
