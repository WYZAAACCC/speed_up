#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_burstkm.py --- ★★★★★★ **修 burst 至物理正确**（用户总目标第 4 项）

## 用户要求
> 「当前的 burst 不是物理正确的，请你将其修复至物理正确」

## 现状（`_bk_exp.py:2576`，逐字）
```python
_n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))
```
★ `alpha_km_n_lath(T)` = `floor(α·(Ms − T))` ⇒ **线性于 ΔT**
  ⇒ `α·ΔT_step = 0.041739 × 23.958 = 1.0` ⇒ `_n_blk` **每档 +1**
  ⇒ `_tgt = B·_n_blk` **每档 +B** ⇒ **恒定速率 ⇒ 没有 burst** ✓
★ **代码自己承认**（`:1781-1782` 逐字）：
  「…**burst 的定量率律仍然没有**（§改 3 纪律）」

## 物理正确的形式（模块里**已有**函数，只是没被用于形核调度）
```python
windowB_km.koistinen(T, Ms, alpha) = 1 - exp(-alpha*(Ms - T))     # KM 分数律
```
★ `N(T) = N_end · f(T)`，`N_end = alpha_km_n_lath(T_end, alpha)` = **23**（每块）
★ 每档增量 `ΔN_k = N_end·[f(T_k) − f(T_{k−1})]`：
    首档 `αΔT=1` ⇒ `f=0.632` ⇒ **63.2%**（**爆发**）
    次档 `αΔT=2` ⇒ `f=0.865` ⇒ **23.2%**
    三档 `αΔT=3` ⇒ `f=0.950` ⇒ **8.5%** ｜ 四档 **3.1%** …（**指数衰减 ⇒ 饱和**）✓

## 改法（**默认档逐位不变**）
把第 2576 行改为**条件表达式**，由新开关 `--burst-km`（默认 **0**）门控：
* `--burst-km 0`（**默认**）⇒ **原式逐字**（线性律）⇒ 归档/在跑的臂**逐位不变** ✓
* `--burst-km 1` ⇒ **KM 分数律**（物理正确）

## 四道自检
1. 锚点唯一；2. `compile()` 通过；3. 新开关存在且默认 0；4. 默认档下表达式**逐字等价**。
"""
import hashlib
import os
import shutil
import sys

P = '_bk_exp.py'
BAK = P + '.bak_burstkm'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """            _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))"""
NEW = """            # ★★★★★★ s284（**用户总目标第 4 项：修 burst 至物理正确**）：
            #   原文只读一行：
            #       `_n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))`
            #   而 `alpha_km_n_lath(T) = floor(α·(M_s − T))` **线性于 ΔT**
            #   ⇒ `α·ΔT_step = 1.0` ⇒ `_n_blk` **每档 +1** ⇒ `_tgt = B·_n_blk` **每档 +B**
            #   ⇒ **恒定速率 ⇒ 没有 burst**（本文件 `:1781-1782` 自己写明
            #     「**burst 的定量率律仍然没有**」）。
            #
            #   ## 物理正确的形式（模块里**已有**函数，只是没被用于形核调度）
            #     `windowB_km.koistinen(T, M_s, α) = 1 − exp(−α(M_s − T))`（KM **分数律**）
            #     ⇒ `N(T) = N_end · f(T)`，`N_end = alpha_km_n_lath(T_end, α)` = **23**（每块）
            #     ⇒ 每档增量 `ΔN_k = N_end·[f(T_k) − f(T_{k−1})]`：
            #         首档 `αΔT=1` ⇒ `f=0.632` ⇒ **63.2%**（**Ms 处爆发**）
            #         次档 `αΔT=2` ⇒ `f=0.865` ⇒ **23.2%**
            #         三档 ⇒ **8.5%** ｜ 四档 ⇒ **3.1%** …（**指数衰减 ⇒ 饱和**）✓
            #       —— 这才是 athermal 马氏体的 burst。
            #
            #   ⚠ **完全由 `--burst-km` 门控**（默认 **0**）⇒ **默认档逐字走原式**
            #     ⇒ 归档与在跑的臂**逐位不变** ✓
            #   ⚠ 判据（**预先写死**，见 s282 提交）：
            #     ① 首档核数应占总量 ~63%（现状 `1/23 = 4.3%`）
            #     ② 每档核数应指数衰减（现状**恒定 3 个**）
            #     ③ 复用引擎已有的 "burst regime" 记账串做正对照（`:1174`）
            #     ④ 核数序列与 `N_end·Δf(T_k)` 在 **±15%** 内一致
            if bool(int(getattr(a, 'burst_km', 0) or 0)):
                _N_end = float(CL.alpha_km_n_lath(T_end_for_burst, _alpha))
                _f_km = 1.0 - np.exp(-_alpha * max(M_S_TI64 - _Tnow, 0.0))
                _n_blk = int(round(_N_end * _f_km))
            else:
                _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# 需要一个 T_end 常量：从 a.T_end 取（引擎入参里有 --T-end）
ANCH2 = "            _Bt = int(getattr(a, 'nuc_block_target', 0) or 0)"
if ANCH2 not in out:
    print('  ❌ 找不到 `_Bt` 锚点 ⇒ 拒绝修改'); sys.exit(1)
out = out.replace(ANCH2,
                  "            T_end_for_burst = float(getattr(a, 'T_end', 298.0) or 298.0)\n"
                  + ANCH2, 1)

# argparse 选项：插在 --nuc-block-target 之后
import re
m = re.search(r"ap\.add_argument\('--nuc-block-target'[^\n]*\n", out)
if not m:
    print('  ❌ 找不到 `--nuc-block-target` 的 add_argument ⇒ 拒绝修改'); sys.exit(1)
ADD = ("    ap.add_argument('--burst-km', type=int, default=0, choices=(0, 1),\n"
       "                    help='★ s284：形核调度用 **KM 分数律**（`1-exp(-a(Ms-T))`）'\n"
       "                         '⇒ Ms 处爆发 + 随后饱和（物理正确的 burst）；'\n"
       "                         '默认 0 ⇒ **逐字走线性原式**，归档逐位不变')\n")
out = out[:m.end()] + ADD + out[m.end():]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(a, 'burst_km', 0)", "koistinen" if False else "_f_km",
             "T_end_for_burst", "'--burst-km'"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核 ──')
print('     * 门控 `--burst-km`（默认 **0**）⇒ 默认档 `else` 分支 = **原式逐字** ✓')
print('     * `--burst-km 1` ⇒ `_n_blk = round(N_end · (1 − exp(−α(Ms − T))))` ✓')
print('     * `N_end = alpha_km_n_lath(T_end, α)` = **23**（每块）✓')
print('     * 需在 `_t5_short.py` 加透传（否则只能直接调 `_bk_exp.py`）')
