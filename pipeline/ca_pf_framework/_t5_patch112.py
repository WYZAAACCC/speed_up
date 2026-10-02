#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_patch112.py --- 修复 s112 的语法错误（把 `--nuc-fresh-every` 透传并入原有 `+` 链）

## 背景（**我犯的错，留痕**）
我在 `_t5_short.py` 的 `--phi-band-every` 之后插了 `] + (…)`，
**与下面已有的 `] +` 括号冲突** ⇒ `SyntaxError: closing parenthesis ']' does not match '('`
⇒ **`_t5_short.py` 一度不可用**（它是长跑恢复的依赖 ⇒ 这是**真实风险**）。
**修法**：把那段 `] + (…)` 删掉，改成把 `--nuc-fresh-every` 的条件项**并入原有的 `+` 链**。
"""
import re
import sys

P = '_t5_short.py'
src = open(P, encoding='utf-8').read()
orig = src

# ── ① 删掉插在 `--phi-band-every` 之后的那个错误片段（`] + (['--nuc-fresh-every' ... else []),`）──
bad = re.search(
    r"\n[ \t]*\] \+ \(\['--nuc-fresh-every', str\(a\.nuc_fresh_every\)\]\n"
    r"[ \t]*if int\(getattr\(a, 'nuc_fresh_every', 0\) or 0\) > 0 else \[\]\),",
    src)
if bad:
    src = src[:bad.start()] + '\n' + src[bad.end():]
    print('  ① 已删除错误的 `] + (…)` 片段')
else:
    print('  ① ⚠ 没找到那个片段（可能已删或格式不同）')

# ── ② 把条件项并入原有的 `+` 链（放在 `--nuc-periodic-seed` 项之前）──
anchor = "             (['--nuc-periodic-seed', '1'] if int(a.periodic_seed) == 1 else []) +"
add = (
    "             # ★★★★★ R581-T5R-s112：`--nuc-fresh-every` 透传"
    "（默认 `0` ⇒ **一个参数都不传** ⇒ 归档路径逐字不变）\n"
    "             #   §111 方案②：显式传**更小的 K** ⇒ 短诊断臂更快尝试 `fresh` ⇒ 拿被拒原因。\n"
    "             (['--nuc-fresh-every', str(a.nuc_fresh_every)]\n"
    "              if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []) +\n"
)
if "nuc-fresh-every', str(a.nuc_fresh_every)" in src and anchor in src:
    # 只补一次
    if "--nuc-fresh-every', str(a.nuc_fresh_every)]\n              if" not in src:
        src = src.replace(anchor, add + anchor, 1)
        print('  ② 已把条件项并入原 `+` 链')
    else:
        print('  ② 已存在（未重复插入）')
else:
    print('  ② ⚠ 锚点没找到：anchor=%s' % (anchor in src))

if src != orig:
    open(P, 'w', encoding='utf-8').write(src)
    print('  已写回 %s' % P)
else:
    print('  未改动')

# ── ③ 语法检查（**必须过**）──
import py_compile
try:
    py_compile.compile(P, doraise=True)
    print('  ✅ py_compile 通过（真跑过）')
except Exception as e:
    print('  ❌ py_compile 仍失败：%s' % e)
    sys.exit(1)

# ── ④ 判据：默认档必须"一个参数都不传" ──
s2 = open(P, encoding='utf-8').read()
ok = "if int(getattr(a, 'nuc_fresh_every', 0) or 0) > 0 else []" in s2
print('  ★ 判据「默认不传」的守卫存在 = %s ⇒ %s' % (ok, 'PASS ✅' if ok else 'FAIL ❌'))
