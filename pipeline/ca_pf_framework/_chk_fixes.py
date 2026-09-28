#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_chk_fixes.py --- Round 83 两处修复的**反向对照**（`MEASUREMENT_SPEC R0`）

修的是什么（见 `WINDOWB_AUDIT_REGISTER.md`）
------------------------------------------
C1 `_sep_conv3` 在 `m > N` 时形状静默出错（实测 N=8：m=9→(6,6,6)）⇒ 现在**抛错**；
   边界 `m == N` 实测本来是对的 ⇒ **必须仍然通过**（反向对照）。
A3 `cover` 空掩模上 `.all()` 返回 True ⇒ "幽灵核"被记为成功 ⇒ 现在**显式拒绝并计数**。

判据
----
  F-1 `m > N` 必须抛 `ValueError`（修前是静默错形状）
  F-2 `m == N` 必须仍然正确（不过度拦截）—— 与 `scipy.ndimage.uniform_filter(mode='wrap')` 比
  F-3 正常 `m=1,2,3` 仍逐位一致
  F-4 空 `cover` 场景：`nucleate()` 的 stack 通道必须**不再**把它记为 `ok`
"""
import os
import sys

os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np                                              # noqa: E402
from scipy import ndimage                                       # noqa: E402
import windowB_surface as W                                     # noqa: E402

N = 8
g = W.LevelSetMulti(N, 4e-7, gamma=0.15, Mob=1e-9, nv=1, df=[0.0, 1e8], reinit_every=0)
f = np.random.default_rng(0).normal(size=(N, N, N))
fails = []

# ---------------- F-1 m > N 必须抛
for m in (9, 11, 20):
    try:
        g._sep_conv3(f, np.ones(2 * m + 1) / (2 * m + 1))
        print('F-1 m=%-3d ⇒ **NO-RAISE（坏）**' % m)
        fails.append('F-1/m=%d' % m)
    except ValueError as e:
        print('F-1 m=%-3d ⇒ 抛 ValueError ✓（%s）' % (m, str(e)[:48]))

# ---------------- F-2 m == N 必须仍正确
k = np.ones(2 * N + 1) / (2 * N + 1)
o = g._sep_conv3(f, k)
ref = ndimage.uniform_filter(f, 2 * N + 1, mode='wrap')
ok2 = np.allclose(o, ref, atol=1e-12)
print('F-2 m=N=%d ⇒ 形状 %s，与 scipy(wrap) 最大差 %.2e ⇒ %s'
      % (N, o.shape, np.abs(o - ref).max(), 'PASS' if ok2 else 'FAIL'))
if not ok2:
    fails.append('F-2')

# ---------------- F-3 常规 m 仍逐位一致
for m in (1, 2, 3):
    kk = np.ones(2 * m + 1) / (2 * m + 1)
    ok3 = np.allclose(g._sep_conv3(f, kk),
                      ndimage.uniform_filter(f, 2 * m + 1, mode='wrap'), atol=1e-12)
    print('F-3 m=%d ⇒ %s' % (m, 'PASS' if ok3 else 'FAIL'))
    if not ok3:
        fails.append('F-3/m=%d' % m)

# ---------------- F-4 空 cover：stack 通道不得记为 ok
#   构造：t 极小（t/2 < dx/2）⇒ cover 为空。用一个薄核 + 已有板条去触发 stack。
g2 = W.LevelSetMulti(32, 1.6e-6, C=None, eps0=None, nv=1, gamma=0.15, Mob=1e-9,
                     df=[0.0, 1e8], workers=1, reinit_every=0)
nz = np.array([0.0, 0.0, 1.0])
g2.seed_plate(1, np.array([8e-7, 8e-7, 8e-7]), nz, 3e-7, 4e-7)
g2.init_parent()
g2.nuc_cfg(R_nuc=1.2e-7, t_nuc=1e-9, n_init=0, seed=3)     # t/2 = 0.5 nm << dx/2
# ★ Round 85：`_npref_of()` 现在是**硬失败**（修 A12：不再静默返回 z 轴）⇒
#   本对照必须在调用 `nucleate()` 之前把惯习面表放好（生产里由 `advance()` 放）。
g2.npref_tab = {1: nz}
ed = np.zeros((2,) + (32, 32, 32))
ed[1] = 1e8
ev = g2.nucleate(ed, n_fresh=0, n_stack=4, f_now=0.0)
dbg = g2._nuc.get('dbg', {})
print('F-4 薄核（t=1 nm, dx=50 nm）⇒ 事件 %d（stack %d）；`dbg`=%s'
      % (len(ev), sum(1 for _, m in ev if m == 'stack'), dbg))
ok4 = dbg.get('empty', 0) > 0 and dbg.get('ok', 0) == 0
print('    ⇒ 空 cover 被显式拒绝（empty=%d）且 ok=0 ⇒ %s'
      % (dbg.get('empty', 0), 'PASS' if ok4 else 'FAIL'))
if not ok4:
    fails.append('F-4')

# ---------------- F-5（Round 92）`norm_smooth` 的 `0<m<1` 必须抛错（否则静默恒等滤波）
g3 = W.LevelSetMulti(24, 1.2e-6, gamma=0.15, Mob=1e-9, nv=1, df=[0.0, 1e8],
                     workers=1, reinit_every=0)
nz3 = np.array([0.0, 0.0, 1.0])
g3.seed_plate(1, np.array([6e-7] * 3), nz3, 2e-7, 2e-7)
g3.init_parent()
try:
    g3.advance(1e-9, aniso=0.4, npref={1: nz3}, band_cells=10, mob_beta=3.5,
               norm_smooth=0.5)
    print('F-5 `norm_smooth=0.5` ⇒ **NO-RAISE（坏：恒等滤波却看似生效）**')
    fails.append('F-5')
except ValueError as e:
    print('F-5 `norm_smooth=0.5` ⇒ 抛 ValueError ✓（%s）' % str(e)[:46])
# 反向对照：合法的 m=1 / m=2 必须仍然可用
for _m in (1, 2):
    try:
        g3.advance(1e-9, aniso=0.4, npref={1: nz3}, band_cells=10, mob_beta=3.5,
                   norm_smooth=_m)
        print('   反向对照 m=%d ⇒ 正常执行 ✓（未过度拦截）' % _m)
    except ValueError as e:
        print('   反向对照 m=%d ⇒ **被误拦**（%s）' % (_m, str(e)[:40]))
        fails.append('F-5/rev%d' % _m)

print('\n【汇总】%s' % ('全部 PASS' if not fails else 'FAIL：%s' % fails))
sys.exit(0 if not fails else 1)
