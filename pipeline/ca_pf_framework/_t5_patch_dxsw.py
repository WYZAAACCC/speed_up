#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch_dxsw.py --- 给 `_t5_short.py` 加 `--dx-nm` 透传（**默认 62.5 ⇒ 逐字不变**）

## 为什么（s287 的关键约束）
`_t5_short.py:44` **硬编码** `'--dx-nm', '62.5'` ⇒ `L = N × 62.5 nm`
⇒ **改 `--N` 只改盒子，不改分辨率**；薄板厚度 `t = 312.5 nm` **恒为 5 个胞**。
★ 而球体基准（`T1_verify_edsign.py`）用 `dx = 20/10 nm`（收敛到 ~2.0e8）
  ⇒ **"薄板 2.96e8 vs 球体 2.0e8"含**分辨率混淆变量**** ⚠
⇒ **必须做**只改 dx** 的单变量对照**才能判"欠解析 vs 物理量" ⇒ 需此透传。

## 改法（**最小、且默认档逐字等价**）
* `'--dx-nm', '62.5',`  →  `'--dx-nm', repr(float(getattr(a, 'dx_nm', 62.5))),`
* 新增 argparse：`--dx-nm`，**默认 62.5** ⇒ **与硬编码值逐字相同** ⇒ 归档**逐位不变** ✓

## 四道自检
1. 锚点唯一；2. `compile()` 通过；3. 新选项存在且默认 62.5；4. 默认档产出同一字符串 `'62.5'`。
   ⚠ 第 4 条要用 `repr(float(62.5))` = `'62.5'` 核对 ⇒ **与原字面量逐字相同** ✓
"""
import hashlib
import os
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_dxsw'
src = open(P, encoding='utf-8').read()
print('  改前 sha256 = %s…（%d 字节）' % (hashlib.sha256(src.encode()).hexdigest()[:16], len(src)))

OLD = """             '--N', str(a.N), '--dx-nm', '62.5',"""
NEW = """             # ★★★★★★ s287：**`--dx-nm` 透传**（原来**硬编码 '62.5'** ⇒ 改 `--N` 只改盒不改分辨率）。
             #   为什么要它：薄板厚度 `t = 312.5 nm` 在 `dx = 62.5 nm` 下**恒为 5 个胞**
             #   ⇒ 与球体基准（`T1_verify_edsign.py` 用 `dx = 20/10 nm`，收敛到 ~2.0e8）
             #     **分辨率差 3–6 倍** ⇒ **"薄板 2.96e8 vs 球体 2.0e8"含混淆变量** ⚠
             #   ⇒ 需做**只改 dx** 的单变量对照，判"**欠解析** vs **物理量**"。
             #   ⚠ **默认 62.5** ⇒ `repr(float(62.5))` = `'62.5'` ⇒ **与原字面量逐字相同**
             #     ⇒ 归档与在跑的臂**逐位不变** ✓
             '--N', str(a.N), '--dx-nm', repr(float(getattr(a, 'dx_nm', 62.5))),"""
n = src.count(OLD)
print('  锚点出现次数 = %d（应为 1）' % n)
if n != 1:
    print('  ❌ 锚点不唯一 ⇒ 拒绝修改'); sys.exit(1)
out = src.replace(OLD, NEW, 1)

# argparse：插在 `--N` 的 add_argument 之后（**括号配平**）
ANCH = "ap.add_argument('--N'"
i = out.find(ANCH)
if i < 0:
    print('  ❌ 找不到 `--N` 的 add_argument ⇒ 拒绝修改'); sys.exit(1)
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
ADD = ("\n    ap.add_argument('--dx-nm', type=float, default=62.5,\n"
       "                    help='★ s287：网格步长（nm）。默认 **62.5** ⇒ 与原来的硬编码值'\n"
       "                         '逐字相同 ⇒ 归档逐位不变；改小 ⇒ 只改分辨率、盒子 L 不变'\n"
       "                         '（薄板厚度将占更多胞 ⇒ 可判\"罚能是否因欠解析偏高\"）')\n")
out = out[:j + 1] + ADD + out[j + 1:]

try:
    compile(out, P, 'exec')
    print('  ✅ 改后语法 OK')
except SyntaxError as e:
    print('  ❌ 语法错误：%s ⇒ 拒绝写盘' % e); sys.exit(1)
for need in ("getattr(a, 'dx_nm', 62.5)", "'--dx-nm', type=float"):
    if need not in out:
        print('  ❌ 校验失败（缺 %r）⇒ 拒绝写盘' % need); sys.exit(1)
if not os.path.exists(BAK):
    shutil.copy2(P, BAK)
    print('  已备份 → %s' % BAK)
open(P, 'w', encoding='utf-8').write(out)
print('  ✅ 已写盘（sha256 %s…，%d 字节）'
      % (hashlib.sha256(out.encode()).hexdigest()[:16], len(out)))
print()
print('  ── 复核（**逐字等价**）──')
print('     * 默认 `dx_nm = 62.5` ⇒ `repr(float(62.5))` = %r' % repr(float(62.5)))
print('     * 原字面量 = %r' % '62.5')
print('     * ⇒ **完全相同** ⇒ 默认档逐位不变 ✓')
