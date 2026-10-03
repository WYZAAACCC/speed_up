#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch122.py --- 给 `_t5_short.py` 加两个透传（`--var-rule` / `--nuc-fresh-every`）

## 安全设计（**s112 事故的教训**）
1. **先备份**；
2. **在内存里改**，改完**立刻 `compile()` 验证**；
3. **只有编译通过才写盘** ⇒ **不可能把语法错误留在文件里**；
4. 写盘后再 `py_compile` + 两条 `grep` 复核。

## 为什么要加（§121 方案）
`--var-rule` 与 `--nuc-fresh-every` 都不在启动器透传里；而它们是把
"单变体单块"变成"多变体多块"的**两个必要条件**（§119 的洞察）。
**⇒ 两处都带"默认档不传"的守卫 ⇒ 归档路径 / 长跑路径逐字不变。**
"""
import re
import shutil
import sys

P = '_t5_short.py'
BAK = P + '.bak_s122'
shutil.copy(P, BAK)
src = open(P, encoding='utf-8').read()
print('  已备份到 %s' % BAK)

# ══════════════════════════════════════════════════════════════════════
# ① argparse：在 `--therm-hist` 的定义之后插入两行
# ══════════════════════════════════════════════════════════════════════
anchor1 = ("    ap.add_argument('--therm-hist', default='linear', choices=('linear', 'lpbf'),\n"
           "                    help='热史：linear（默认，归档）| lpbf（S14，未过 6a/6b/6c 勿用于结论）')\n")
add1 = (
    "    # ★★★★★ R581-T5R-s122：**两个透传**（把\"单变体单块\"变成\"多变体多块\"的必要条件）\n"
    "    #   `--var-rule`：变体选择（**只对 `fresh` 通道生效**；`ed`=归档默认 ⇒ 不传）\n"
    "    #   `--nuc-fresh-every`：`fresh` 通道周期（`0`=引擎自动取 `K=n(T_end)` ⇒ 不传）\n"
    "    ap.add_argument('--var-rule', default='ed', choices=('ed', 'random', 'doublet'),\n"
    "                    help='变体选择（只对 fresh 生效）：ed=归档默认 | random | doublet')\n"
    "    ap.add_argument('--nuc-fresh-every', type=int, default=0,\n"
    "                    help='fresh 周期（0=引擎自动取 K=n(T_end)；>0=显式）')\n")
if anchor1 in src:
    src = src.replace(anchor1, anchor1 + add1, 1)
    print('  ① argparse 两行已插入')
else:
    print('  ① ⚠ 锚点没找到 ⇒ **中止**（不改盘）')
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
# ② build()：并入**已有的 `+` 链**（**不新开 `] +`** —— s112 正是错在这里）
# ══════════════════════════════════════════════════════════════════════
# ⚠ s122 留痕：第一版锚点我写成 **13 个空格**，而实际是 **12 个**
#   （`grep -n 'nuc-periodic-seed' _t5_short.py | cat -A` 实测：`            (` = 12 空格）
#   ⇒ 补丁**安全中止、未写盘**（这正是"先编译、通过才写"设计的目的）。
anchor2 = "            (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else []) +"
add2 = (
    "            # ★★★★★ R581-T5R-s122：两个透传（**默认档不传** ⇒ 归档/长跑逐字不变）\n"
    "            (['--var-rule', str(getattr(a, 'var_rule', 'ed'))]\n"
    "             if str(getattr(a, 'var_rule', 'ed')) != 'ed' else []) +\n"
    "            (['--nuc-fresh-every', str(a.nuc_fresh_every)]\n"
    "             if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []) +\n")
if anchor2 in src:
    src = src.replace(anchor2, add2 + anchor2, 1)
    print('  ② build() 的条件项已并入原 `+` 链')
else:
    print('  ② ⚠ 锚点没找到 ⇒ **中止**（不改盘）')
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════
# ③ ★★★ **先编译，通过才写盘**
# ══════════════════════════════════════════════════════════════════════
try:
    compile(src, P, 'exec')
    print('  ③ ★ 内存编译通过 ⇒ 写盘')
except SyntaxError as e:
    print('  ③ ❌ 编译失败（**不写盘**，原文件保持完好）：%s' % e)
    sys.exit(1)
open(P, 'w', encoding='utf-8').write(src)

# ══════════════════════════════════════════════════════════════════════
# ④ 写盘后复核（**四条判据**）
# ══════════════════════════════════════════════════════════════════════
import py_compile
s2 = open(P, encoding='utf-8').read()
print()
print('  ── 复核（四条判据，预先写死）──')
ok = True
try:
    py_compile.compile(P, doraise=True)
    print('    ① py_compile                 ⇒ ✅ PASS')
except Exception as e:
    print('    ① py_compile                 ⇒ ❌ FAIL: %s' % e); ok = False
n1 = s2.count("['--var-rule', str(getattr(a, 'var_rule', 'ed'))]")
print('    ② var-rule 透传出现次数 = %d   ⇒ %s' % (n1, '✅ PASS' if n1 == 1 else '❌ FAIL'))
ok &= (n1 == 1)
n2 = s2.count("['--nuc-fresh-every', str(a.nuc_fresh_every)]")
print('    ③ fresh-every 透传出现次数 = %d ⇒ %s' % (n2, '✅ PASS' if n2 == 1 else '❌ FAIL'))
ok &= (n2 == 1)
bad = "] + (['--var-rule'" in s2 or "] + (['--nuc-fresh-every'" in s2
print('    ④ 无新开 `] +`（s112 的错法）  ⇒ %s' % ('❌ FAIL' if bad else '✅ PASS'))
ok &= (not bad)
print()
print('  ⇒ **%s**' % ('全部通过' if ok else '有未通过项 —— 需人工核对（备份在 %s）' % BAK))
sys.exit(0 if ok else 1)
