#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_fix_ellipse.py --- ★★★★★ 修 `windowB_surface.py` 里 `ellipse` 分支的 `sorted(数组)` BUG

## BUG（实测 traceback）
```
windowB_surface.py:4678   （`mob_iform == 'ellipse'` 分支内）
  _nh2 = (np.asarray(sorted(npref.values())[0], float).ravel() ...
ValueError: The truth value of an array with more than one element is ambiguous.
```
**根因**：`npref` 的**值是三维法向矢量（numpy 数组）**，而 `sorted()` 用 `<` 逐对比较
⇒ 长度 >1 的数组比较返回**布尔数组** ⇒ `ValueError`。
**⇒ 这个分支**从来没被成功跑过**** —— 一进入就崩（实测两臂都在 step 0 退出，`exit=1`）。

## 修法（**最小、保持作者意图**）
**同一段代码的下一行是 `_wv2 = np.asarray(_wt2[1], float).ravel()` ⇒ 作者意图是"取**某一个变体**的轴"。**
⇒ **按**键**排序取第一个键**（`sorted(npref.keys())[0]`）而不是按**值**排序。
**⇒ 语义不变（仍是"取第一个变体的法向"），只是**不再对数组做比较****。

## 安全性（**关键**）
**本段被 `mob_iform == 'ellipse'` 闸住，而它的默认值是 `'exp2'`**
⇒ **默认路径**不进入**本分支 ⇒ **对所有已跑/在跑的臂**零影响**（逐位不变）。
**⚠ 但仍须记账并按"改引擎"处理：跑一个短程正/负对照。**
"""
import shutil
import sys

P = 'windowB_surface.py'
BAK = P + '.bak_ellipse'
shutil.copy(P, BAK)
src = open(P, encoding='utf-8').read()
print('  已备份到 %s' % BAK)

BAD = "            _nh2 = (np.asarray(sorted(npref.values())[0], float).ravel()\n" \
      "                    if isinstance(npref, dict) else np.asarray(npref, float).ravel())\n"
GOOD = ("            # ★★★★★ R581-T5R-s231（**我修的框架 BUG**，实测 traceback 见 _t5_amtrace.sh）：\n"
        "            #   原代码是 `sorted(npref.values())[0]` —— 而 `npref` 的**值是三维法向数组**，\n"
        "            #   `sorted()` 用 `<` 逐对比较 ⇒ 长度>1 的数组返回**布尔数组** ⇒\n"
        "            #   `ValueError: truth value ... is ambiguous` ⇒ **本分支从来没跑起来过**\n"
        "            #   （实测：开 `--mob-iform ellipse` 的两臂都在 step 0 以 exit=1 退出）。\n"
        "            #   修法（**保持作者意图**）：下一行 `_wv2 = _wt2[1]` 说明意图是"
        "\"取某一个变体的轴\"\n"
        "            #   ⇒ 改为**按键**排序取第一个键（不再对数组做比较）。\n"
        "            #   ⚠ 安全性：本段被 `mob_iform == 'ellipse'` 闸住（默认 'exp2'）\n"
        "            #     ⇒ **默认路径不进入 ⇒ 对所有已跑/在跑的臂逐位不变**。\n"
        "            _npk = (sorted(npref.keys())[0] if isinstance(npref, dict) else None)\n"
        "            _nh2 = (np.asarray(npref[_npk], float).ravel()\n"
        "                    if isinstance(npref, dict) else np.asarray(npref, float).ravel())\n")

if BAD not in src:
    print('  ⚠ 锚点没找到（可能已被修过）⇒ 中止，不改'); sys.exit(1)
src = src.replace(BAD, GOOD, 1)
print('  ① BUG 行已替换')

try:
    compile(src, P, 'exec')
    print('  ② ★ 内存编译通过 ⇒ 写盘')
except SyntaxError as e:
    print('  ② ❌ 编译失败（不写盘）：%s' % e); sys.exit(1)
open(P, 'w', encoding='utf-8').write(src)

import py_compile
s2 = open(P, encoding='utf-8').read()
print()
print('  ── 复核 ──')
ok = True
try:
    py_compile.compile(P, doraise=True); print('    ① py_compile ⇒ ✅')
except Exception as e:
    print('    ① py_compile ⇒ ❌ %s' % e); ok = False
print('    ② 旧 BUG 行残留次数 = %d ⇒ %s'
      % (s2.count('sorted(npref.values())'), '✅ 已清除' if s2.count('sorted(npref.values())') == 0 else '❌'))
print('    ③ 新行存在次数 = %d ⇒ %s'
      % (s2.count('_npk = (sorted(npref.keys())[0]'), '✅' if s2.count('_npk = (sorted(npref.keys())[0]') == 1 else '❌'))
print('    ④ ellipse 闸门仍在 = %s'
      % ('✅' if "mob_iform == 'ellipse'" in s2 else '❌'))
ok &= (s2.count('sorted(npref.values())') == 0)
print()
print('  ⇒ **%s**' % ('修好' if ok else '有未过项（备份在 %s）' % BAK))
sys.exit(0 if ok else 1)
