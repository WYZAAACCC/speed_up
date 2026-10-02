#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_6b_chk.py --- ★★★★★ 复核清单 **6b** 的三条判据（**全部预先写死**）

| 判据 | 内容 | 为什么 |
|---|---|---|
| **6b-①** | 分支走了（横幅出现、未回退）| 已由短跑 PASS |
| **6b-②** | **`T_lpbf(t=0) ≈ T_start`（±1 K）** | 引擎的 `t=0` 是 athermal 时钟起点 ⇒ **时间原点必须对齐** |
| **6b-③** | **存在一步 `T_lpbf > T_linear + 1 K`**（再热证据）| 若没有，说明热循环**没生效** |
"""
import sys

sys.path.insert(0, '.')
from _t5_therm import lpbf_like_linear                        # noqa: E402

T_START, T_END, T_COOL = 849.041591796641, 298.0, 2.3425e-04
f = lpbf_like_linear(T_START, T_END, T_COOL)
# `linear_cool` 的同参数对照（解析式：线性从 T_start 降到 T_end）
def lin(t):
    return max(T_END, T_START - (T_START - T_END) * (t / T_COOL))

print('=' * 92)
print('复核清单 6b：三条判据（预先写死）')
print('=' * 92)
# ── 6b-② ──
T0 = f(0.0)
d = abs(T0 - T_START)
ok2 = d <= 1.0
print('  6b-② `T_lpbf(t=0)` = **%.2f K**，目标 `T_start` = %.2f K，差 = **%+.3f K**'
      % (T0, T_START, T0 - T_START))
print('        判据 |差| <= 1 K ⇒ **%s**' % ('PASS ✅' if ok2 else 'FAIL ❌'))
# ── 6b-③ ──
worst = 0.0
worst_t = 0.0
for i in range(200001):
    t = T_COOL * 4.0 * i / 200000.0
    dd = f(t) - lin(t)
    if dd > worst:
        worst, worst_t = dd, t
ok3 = worst > 1.0
print('  6b-③ `max(T_lpbf − T_linear)` = **%+.2f K** @ t = %.4g s' % (worst, worst_t))
print('        判据 > +1 K ⇒ **%s**' % ('PASS ✅' if ok3 else 'FAIL ❌'))
print()
print('  ── 附：偏移与全温程记账 ──')
print('     t_off = %.6g s   T_at_0 = %.2f K   offset_ok = %s'
      % (f.dbg['t_off'], f.dbg['T_at_0'], f.dbg['offset_ok']))
print('     `.band` = %s   `.band_full` = %s' % (f.band, f.band_full))
print('     峰值 = %s' % (f.peaks,))
print()
allok = ok2 and ok3
print('  ⇒ **6b %s**' % ('PASS ✅（三条判据全过）' if allok else 'FAIL ❌'))
print('=' * 92)
sys.exit(0 if allok else 1)
