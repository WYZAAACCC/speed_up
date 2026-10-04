#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fix_burstkm.py --- 修 `_t5_patch_burstkm.py` 的插入点（**用括号配平，不用单行正则**）

## 上一版失败的原因（已记账）
`--nuc-block-target` 的 `add_argument(...)` **跨多行**，而我用
`re.search(r"ap\\.add_argument\\('--nuc-block-target'[^\\n]*\\n")` 只匹配了**第一行**
⇒ 新选项被插到**调用中间** ⇒ `SyntaxError (line 3688)` ⇒ **patcher 在写盘前就退出了
⇒ `_bk_exp.py` 未被改动** ✓（自检起作用了）

## 本版做法
用**括号配平**找 `--nuc-supercrit` 那个 `add_argument(...)` 的**真正结尾**，再插入。
"""
import hashlib
import os
import shutil
import sys

P = '_bk_exp.py'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

# ① 替换 `_n_blk` 那一行（若已改过则跳过）
OLD = """            _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))"""
NEW = """            # ★★★★★★ s284（**用户总目标第 4 项：修 burst 至物理正确**）
            #   原文一行：`_n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))`，
            #   而 `alpha_km_n_lath(T) = floor(α·(M_s − T))` **线性于 ΔT**
            #   ⇒ `α·ΔT_step = 1.0` ⇒ `_n_blk` **每档 +1** ⇒ `_tgt = B·_n_blk` **每档 +B**
            #   ⇒ **恒定速率 ⇒ 没有 burst**（本文件 `:1781-1782` 自己写明
            #     「**burst 的定量率律仍然没有**」）。
            #   ## 物理正确的形式（模块里**已有**函数，只是没被用于形核调度）
            #     `windowB_km.koistinen(T, M_s, α) = 1 − exp(−α(M_s − T))`（KM **分数律**）
            #     ⇒ `N(T) = N_end · f(T)`，`N_end = alpha_km_n_lath(T_end, α)` = **23** 每块
            #     ⇒ 每档增量 `ΔN_k = N_end·Δf(T_k)`：
            #         首档 `αΔT=1` ⇒ `f=0.632` ⇒ **63.2%**（**Ms 处爆发**）
            #         次档 ⇒ **23.2%** ｜ 三档 ⇒ **8.5%** ｜ 四档 ⇒ **3.1%** …（**指数衰减**）✓
            #   ⚠ 完全由 `--burst-km` 门控（默认 **0**）⇒ 默认档**逐字走原式**
            #     ⇒ 归档与在跑的臂**逐位不变** ✓
            if bool(int(getattr(a, 'burst_km', 0) or 0)):
                _N_end = float(CL.alpha_km_n_lath(float(getattr(a, 'T_end', 298.0) or 298.0),
                                                  _alpha))
                _f_km = 1.0 - np.exp(-_alpha * max(M_S_TI64 - _Tnow, 0.0))
                _n_blk = int(round(_N_end * _f_km))
            else:
                _n_blk = int(np.floor(CL.alpha_km_n_lath(_Tnow, _alpha) + 1e-12))"""
n1 = src.count(OLD)
print('  ① `_n_blk` 锚点出现次数 = %d（应为 1）' % n1)
if n1 != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# ② 找 `--nuc-supercrit` 的 add_argument 并**括号配平**到结尾，在其后插入新选项
ANCH = "add_argument('--nuc-supercrit'"
i = out.find(ANCH)
if i < 0:
    print('  ❌ 找不到 `--nuc-supercrit` 锚点 ⇒ 拒绝修改'); sys.exit(1)
j = i
depth = 0
while j < len(out):
    if out[j] == '(':
        depth += 1
    elif out[j] == ')':
        depth -= 1
        if depth == 0:
            break
    j += 1
ADD = ("\n    ap.add_argument('--burst-km', type=int, default=0, choices=(0, 1),\n"
       "                    help='★ s284：形核调度用 **KM 分数律** `1-exp(-a(Ms-T))`'\n"
       "                         '⇒ Ms 处爆发 + 随后饱和（物理正确的 burst）；'\n"
       "                         '默认 0 ⇒ 逐字走线性原式，归档逐位不变')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(a, 'burst_km', 0)", "_f_km", "'--burst-km'"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(P + '.bak_burstkm'):
    shutil.copy2(P, P + '.bak_burstkm')
    print('  已备份 → %s.bak_burstkm' % P)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核 ──')
print('     * 门控 `--burst-km`（默认 **0**）⇒ 默认档 = **原式逐字** ✓')
print('     * `--burst-km 1` ⇒ `_n_blk = round(N_end·(1 − exp(−α(Ms − T))))` ✓')
print('     * 下一步：给 `_t5_short.py` 加透传')
