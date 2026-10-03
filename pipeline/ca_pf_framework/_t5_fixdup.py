#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fixdup.py --- 修掉 `--nuc-fresh-every` 的**重复定义**（我自己的补丁造成的）

## 事故链（**留痕**）
* **s112**：我尝试加 `--nuc-fresh-every` 的 argparse 行；那次运行**先执行了 argparse 部分**
  （写在文件更前面），**之后才撞上我自己造成的 `SyntaxError`** ⇒ **那一行留在了文件里**。
* **s122**：我的补丁**又加了一遍**（它只检查语法、不检查"参数是否已存在"）⇒ **重复定义**。
* **后果**：`argparse.ArgumentError: conflicting option string` ⇒
  **`_t5_short.py` 任何调用都失败** ⇒ **长跑的 `--resume` 入口被破坏**（真实风险）。

## 修法（**自验证：先编译、通过才写盘**）
删掉**多余的**那一处定义（保留带 s122 注释的那一处）。
"""
import re
import shutil
import sys

P = '_t5_short.py'
shutil.copy(P, P + '.bak_dupfix')
src = open(P, encoding='utf-8').read()
print('  已备份到 %s' % (P + '.bak_dupfix'))

# 找出全部 `--nuc-fresh-every` 的 add_argument 块（含其 help 续行）
pat = re.compile(
    r"    ap\.add_argument\('--nuc-fresh-every', type=int, default=0,\n"
    r"                    help='[^']*'\)\n")
hits = list(pat.finditer(src))
print('  找到 %d 处 `--nuc-fresh-every` 的定义' % len(hits))
if len(hits) <= 1:
    print('  ⇒ 只有 %d 处 ⇒ **无需修**（或格式不同，需人工核对）' % len(hits))
    sys.exit(0)

# 保留**最后一处**（带 s122 注释的），删掉前面的
kill = hits[:-1]
for m in reversed(kill):
    # 连同紧邻的 s112 遗留注释一起删（若存在）
    start = m.start()
    pre = src[max(0, start - 400):start]
    cm = None
    for line in reversed(pre.split('\n')):
        if 'fresh' in line and line.strip().startswith('#'):
            cm = line
        elif cm is not None and not line.strip().startswith('#'):
            break
    src = src[:start] + src[m.end():]
print('  已删除 %d 处多余定义（保留最后 1 处）' % len(kill))

# ── 先编译，通过才写盘 ──
try:
    compile(src, P, 'exec')
    print('  ★ 内存编译通过 ⇒ 写盘')
except SyntaxError as e:
    print('  ❌ 编译失败（**不写盘**）：%s' % e)
    sys.exit(1)
open(P, 'w', encoding='utf-8').write(src)

# ── 写盘后复核 ──
import py_compile
s2 = open(P, encoding='utf-8').read()
n = s2.count("add_argument('--nuc-fresh-every'")
print()
print('  ── 复核（三条判据）──')
ok = True
try:
    py_compile.compile(P, doraise=True)
    print('    ① py_compile                          ⇒ ✅ PASS')
except Exception as e:
    print('    ① py_compile                          ⇒ ❌ FAIL: %s' % e); ok = False
print('    ② `--nuc-fresh-every` 定义数 = %d      ⇒ %s'
      % (n, '✅ PASS' if n == 1 else '❌ FAIL'))
ok &= (n == 1)
nv = s2.count("add_argument('--var-rule'")
print('    ③ `--var-rule` 定义数 = %d             ⇒ %s'
      % (nv, '✅ PASS' if nv == 1 else '❌ FAIL'))
ok &= (nv == 1)
print()
print('  ⇒ **%s**' % ('全部通过' if ok else '有未通过项 —— 需人工核对（备份在 %s.bak_dupfix）' % P))
sys.exit(0 if ok else 1)
