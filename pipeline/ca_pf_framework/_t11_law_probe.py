#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_law_probe.py —— **直接调引擎用的那个函数**，量出 `n_lath_int` 的真值。

## 为什么要它（不能再推理）
  生产跑的事件行写「累计 3/9（本档目标；每块口径 **23**）」，而按代码
  `_n_blk = int(floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))`（`_bk_exp.py:2911`）
  与 `_tgt = min(_Bt*_n_blk, nv)`（`:2943`）我**算不出 9**。
  `AGENTS.md`：**推理不算数** ⇒ **直接调函数、把返回值打出来**。
"""
import sys

sys.path.insert(0, '.')
import windowB_closure as CL          # noqa: E402

ALPHA = 0.041739
MS = None
try:
    from windowB_km import M_S_TI64 as MS   # noqa: E402
except Exception:                            # noqa: BLE001
    pass

print(f"alpha   = {ALPHA}")
print(f"M_s     = {MS}")
if MS is not None:
    print("\n各档温度处的 n_lath_int（= floor(α·ΔT)）：")
    for k in (1, 2, 3, 8, 9, 10, 15, 22):
        T = MS - k / ALPHA
        try:
            v = CL.alpha_km_n_lath(T, ALPHA)
        except Exception as e:                # noqa: BLE001
            v = f"<异常 {e}>"
        try:
            vi = CL.n_lath_int(T, ALPHA)
        except Exception as e:                # noqa: BLE001
            vi = f"<异常 {e}>"
        print(f"  k={k:>3}  T={T:8.2f} K   alpha_km_n_lath={v!r}   n_lath_int={vi!r}")
    print(f"\n  T_end=298 ⇒ n_lath_int = {CL.n_lath_int(298.0, ALPHA)!r}"
          f"   （日志里『每块口径』= 23 ⇒ 应与此一致）")
print("\n模块里可用的相关函数：")
print("  " + ", ".join(n for n in dir(CL) if 'lath' in n.lower()
                       or 'alpha' in n.lower() or 'km' in n.lower()))
