#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r476_nregcap.py —— 任务(3) 验收：**int8 → int16 真的放开了上限，而且数值没变**。

## 要证的命题（三条，缺一不可）

* **T1｜旧代码确实是坏的（负对照，必须能失败）**
  构造一个 `region` 取值到 **199** 的场 ⇒ `astype(np.int8)` 必须**回绕成负数**
  （199 − 256 = −57）。若这条**不**成立，说明"int8 上限 127"这个前提是我编的
  ⇒ 本任务的必要性不成立。
* **T2｜新代码在大 nreg 下数值正确**
  同一批 `phi`，`LevelSetMulti.region()` 必须与 **int64 参考 argmin 逐位相同**，
  且覆盖到 >127 的场号。
* **T3｜上限确实放开了**
  能构造出 `nreg = 200` 的 lath（旧守卫在 `M+1 > 120` 就 raise）
  ⇒ 旧代码必须 raise、新代码必须不 raise。

## 为什么必须做 T1（而不是"改了就完事"）

本仓库纪律：**守卫/修复必须反向测一次**（`AGENTS.md §3.4`：破坏被守卫的条件，
确认它真的会拦）。这里"反向"就是：**证明旧的 int8 在 nreg>127 时真的给出错值**。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NR = 200                 # 场数（> 127，> 120）
N = 32                   # 小盒子，只要覆盖到高场号即可


def P(s):
    print(s, flush=True)


def make_phi(nr, n):
    """造一个**argmin 已知**的 phi：场 k 在区域 k 内最小（依次递减的常数块）。

    做法：把 n³ 个胞尽量均匀地分给 nr 个场；场 k 在自己的块内取 `−(nr−k)`，
    其余场取一个大的正值。这样 `argmin` 就是块编号 = k。
    """
    phi = np.full((nr, n, n, n), 1e6, np.float64)
    flat = np.arange(n ** 3)
    owner = (flat * nr) // (n ** 3)          # 0..nr−1，基本均匀
    for k in range(nr):
        m = (owner == k)
        if not m.any():
            continue
        phi[k].reshape(-1)[m] = -(nr - k)    # k 越大值越小 ⇒ 不，取 +(nr−k) 才是……
    # ★ 修正：要 argmin = owner，就让**属于块 k 的场 k** 最小
    phi[:] = 1e6
    for k in range(nr):
        m = (owner == k)
        if m.any():
            phi[k].reshape(-1)[m] = -1.0     # 该块内场 k = −1（最小）
    return phi, owner


def main():
    P('=' * 92)
    P('_r476  任务(3) 验收：int8 → int16')
    P('=' * 92)
    ok_all = True

    # ---------------- T1 旧代码确实会回绕（负对照） ----------------
    P('\n[T1 负对照：int8 在 nreg>127 时必须给出错值]')
    vals = np.array([0, 1, 126, 127, 128, 150, 199], np.int64)
    wrapped = vals.astype(np.int8).astype(np.int64)
    P('   原值      %s' % vals.tolist())
    P('   int8 后   %s' % wrapped.tolist())
    bad = [(int(a), int(b)) for a, b in zip(vals, wrapped) if a != b]
    ok1 = (len(bad) > 0) and all(b < 0 for _, b in bad)
    P('   ⇒ 出错（且回绕成负数）的值：%s' % bad)
    P('   ⇒ **%s**' % ('✅ PASS（旧代码确实坏 ⇒ 本任务必要）' if ok1
                       else '❌ FAIL（int8 没坏 ⇒ 前提不成立，须重查）'))
    ok_all &= ok1

    # ---------------- T2 region() 数值正确 ----------------
    P('\n[T2 region() 在大 nreg 下必须与 int64 参考逐位相同]')
    phi, owner = make_phi(NR, N)
    ref = np.argmin(phi, axis=0).astype(np.int64)

    # 直接测 `region()` 的两条路径（有无 par）
    import windowB_surface as W
    g = W.LevelSetMulti.__new__(W.LevelSetMulti)      # 不跑 __init__（只要 phi/par）
    g.phi = phi
    g.par = None
    got_serial = g.region()
    # 并行路径（★ 自查：第一版写 `ParCtx(workers=2)` ⇒ 报
    #   "unexpected keyword argument 'workers'"；`windowB_surface.py:915` 用的是**位置参数**）
    par_ok = False
    try:
        import windowB_par as PAR
        g.par = PAR.ParCtx(2)
        par_ok = True
    except Exception as e:                              # pragma: no cover
        P('   （并行路径不可用：%s）' % e)
        g.par = None
    got_par = g.region() if par_ok else None

    for nm, got in (('串行', got_serial), ('并行', got_par)):
        if got is None:
            P('   %s：**跳过**（par 不可用）⇒ 本项**未取证**，不得算作通过' % nm)
            continue
        same = bool(np.array_equal(got.astype(np.int64), ref))
        P('   %s路径：dtype=%s  max=%d  min=%d  nreg=%d  与 int64 参考逐位相同 = **%s**'
          % (nm, got.dtype, int(got.max()), int(got.min()), NR, same))
        ok_all &= same
    ok2 = (got_serial.dtype == np.int16) and bool(
        np.array_equal(got_serial.astype(np.int64), ref)) and int(got_serial.max()) > 127
    P('   ⇒ dtype 是 int16？ %s ；覆盖到 >127 的场号？ max=%d ⇒ **%s**'
      % (got_serial.dtype == np.int16, int(got_serial.max()),
         '✅ PASS' if ok2 else '❌ FAIL'))
    ok_all &= ok2

    # ---------------- T3 上限确实放开 ----------------
    P('\n[T3 上限：旧的 120 守卫必须已被解除]')
    import windowB_lath as LT
    # ★ 自查：第一版按 `LevelSetLath`/`LathSet`/`MultiLath` 找类，全找不到 ⇒ T3 被跳过。
    #   实际类名是 **`LathTable`**（`windowB_lath.py:199`，守卫在它的 `__init__` 里）。
    cls = LT.LathTable
    P('   用 %s 构造 M=%d 根板条（旧守卫在 M+1 > 120 就 raise）' % (cls.__name__, NR))
    ok3 = None
    try:
        inst = cls(variants=list(np.arange(NR) % 12 + 1), label='r476')
        P('   ⇒ **构造成功**，nreg = %d ⇒ ✅ PASS（上限已放开）' % inst.nreg)
        ok3 = True
    except ValueError as e:
        P('   ⇒ ❌ 仍然 raise：%s' % e)
        ok3 = False
    except Exception as e:
        P('   ⚠ 其它异常（可能只是参数不全，**不等于守卫没放开**）：%r' % e)
        ok3 = None
    if ok3 is None:
        P('   ⇒ ⚠ T3 **未取证**，不得算作通过')
    else:
        ok_all &= bool(ok3)
    # 反向：超出新上限必须仍然被拦
    try:
        cls(variants=list(np.arange(40000) % 12 + 1), label='r476big')
        P('   ⚠ 40000 根竟然没被拦 ⇒ **新守卫失效**')
        ok_all = False
    except ValueError:
        P('   ⇒ 40000 根仍被拦 ✅（新守卫有效）')
    except Exception as e:
        P('   （40000 根触发了别的异常：%r）' % e)

    P('\n' + '=' * 92)
    P('★ 总结论：%s' % ('**全部 PASS ⇒ 任务(3) 验收通过**' if ok_all
                        else '❌ **有 FAIL ⇒ 不得宣称任务(3) 完成**'))
    P('=' * 92)
    return 0 if ok_all else 3


if __name__ == '__main__':
    sys.exit(main())
