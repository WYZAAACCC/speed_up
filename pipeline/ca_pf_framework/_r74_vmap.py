#!/usr/bin/env python3
"""R74: 把 `vmap` 挂到引擎对象上 ⇒ 让 `facet_project()` 的 `excl` 真正生效。

## 依据（`R30_AUDIT_LEDGER.md` §77）
`facet_project()` 里用 `getattr(self, 'vmap', None)` 取"场→变体"映射，
而 **`LevelSetMulti` 没有这个属性，也没从构造函数收到变体信息**
（`__init__` 只有 `nv`/`eps0`/`npref_tab` 等，全部按**场号**索引）
⇒ `vs = {}` ⇒ `excl` 恒为 `None` ⇒ 新分支**从未生效**
⇒ 实测 `m3out10` 与 `m3fp10` **逐位相同**。

修法：`_bk_exp.py` 手里本来就有 `vmap` ⇒ 构造完 `g` 之后**挂上去**。
⚠ 只**新增属性**，不改变任何既有代码路径 ⇒ 默认行为不变。
"""
import os
import re

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
p = '_bk_exp.py'
s = open(p, encoding='utf-8').read()
print('替换前出现次数:', s.count('g.advance(dt, **kw)'))
if 'g.vmap = dict(vmap)' in s:
    print('已经挂过，跳过')
else:
    s = s.replace(
        'g.advance(dt, **kw)',
        '# ★★★★★ R74（`R30_AUDIT_LEDGER.md` §77）：把"场→变体"映射挂到引擎对象上。\n'
        '            #   为什么：`LevelSetMulti.facet_project()` 需要它来构造"同变体的其他场"\n'
        '            #   排除掩码（只投影外侧，保根数）。引擎**没有**这个属性，也没从构造\n'
        '            #   函数收到变体信息（`__init__` 里全部按**场号**索引）⇒ `excl` 曾恒为\n'
        '            #   `None`，导致 §76 的"只投影外侧已生效"是**错的**（§77 已更正）。\n'
        '            #   ⚠ 只新增属性 ⇒ 不影响任何既有路径。\n'
        '            g.vmap = dict(vmap)\n'
        '            g.advance(dt, **kw)',
        1)
    open(p, 'w', encoding='utf-8').write(s)
    print('已写入；替换后出现次数:', s.count('g.vmap = dict(vmap)'))
# 语法检查
import ast
try:
    ast.parse(open(p, encoding='utf-8').read())
    print('SYNTAX-OK')
except Exception as e:
    print('SYNTAX-FAIL', e)
