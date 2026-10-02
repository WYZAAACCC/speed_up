#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_loopstate.py --- ★★★★★ **机械地**列出主循环体里被赋值的**所有**变量

## 为什么不用 grep
**"grep 没搜到 ≠ 代码里没有"**（P28）。而且循环体有 ~450 行、含多层缩进与
注释里的伪代码 ⇒ **必须按 AST 解析**，才能既不漏（注释里的、嵌套里的）
也不误报（注释掉的行、字符串里的）。

## 口径
* 只统计**循环体内部**（`for it in range(...)` 的 body）的赋值
* 分别标出：**每个 `it` 都赋**、**条件赋**（在 if 里）、**只赋一次**（在 if it==0 等里）
* 同时抓 `g.X = ...` 这类**对引擎对象的改写**（那也是状态！）
"""
import ast
import sys
from collections import defaultdict

SRC = sys.argv[1] if len(sys.argv) > 1 else '_bk_exp.py'
LOOP_LINE = int(sys.argv[2]) if len(sys.argv) > 2 else 1742

src = open(SRC, encoding='utf-8', errors='replace').read()
tree = ast.parse(src)
lines = src.split('\n')


def find_loop(node):
    """找 lineno == LOOP_LINE 的 For"""
    for n in ast.walk(node):
        if isinstance(n, ast.For) and n.lineno == LOOP_LINE:
            return n
    return None


loop = find_loop(tree)
if loop is None:
    print('  ⚠ 没找到 lineno=%d 的 For' % LOOP_LINE)
    raise SystemExit(1)

end = max(getattr(n, 'lineno', 0) for n in ast.walk(loop))
print('=' * 100)
print('主循环体：第 %d 行 ~ 第 %d 行（共 %d 行）' % (loop.lineno, end, end - loop.lineno + 1))
print('=' * 100)

plain = defaultdict(list)     # 名字 -> [行号]
attr = defaultdict(list)      # obj.attr -> [行号]
aug = defaultdict(list)       # += 等
sub = defaultdict(list)       # 下标赋值 / 方法调用

for n in ast.walk(loop):
    ln = getattr(n, 'lineno', 0)
    if isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name):
                plain[t.id].append(ln)
            elif isinstance(t, ast.Attribute):
                attr['%s.%s' % (ast.unparse(t.value), t.attr)].append(ln)
            elif isinstance(t, ast.Subscript):
                sub[ast.unparse(t)[:50]].append(ln)
    elif isinstance(n, ast.AugAssign):
        t = n.target
        if isinstance(t, ast.Name):
            aug[t.id].append(ln)
        elif isinstance(t, ast.Attribute):
            aug['%s.%s' % (ast.unparse(t.value), t.attr)].append(ln)
    elif isinstance(n, ast.AnnAssign) and n.target.__class__ is ast.Name:
        plain[n.target.id].append(ln)


def show(title, d, note=''):
    print()
    print('  ── %s（%d 个）%s──' % (title, len(d), note))
    for k in sorted(d):
        ls = sorted(set(d[k]))
        # 判断是否每轮都赋：粗略用"是否不在 if 里"⇒ 这里给行号让人核
        print('    %-28s 行 %s' % (k, ','.join(str(x) for x in ls[:8])
                                   + ('…' if len(ls) > 8 else '')))


show('**普通变量赋值**（`X = ...`）', plain)
show('**引擎对象改写**（`g.X = ...` 等）', attr)
show('**自增/自改**（`X += ...`）', aug)
show('**下标/切片赋值**（`X[i] = ...`）', sub)

print()
print('=' * 100)
print('  ★ 读法：')
print('   · **普通变量**里，凡是"每轮都可能变"的 ⇒ **续跑必须存**')
print('   · **`g.X = ...`** ⇒ 那是**引擎对象**上的状态 ⇒ 也必须存（或由引擎自身构造恢复）')
print('   · **`X += ...`** ⇒ 累积量 ⇒ **路径相关** ⇒ 必存')
print('   · **`X[i] = ...`** ⇒ 列表/数组就地改写 ⇒ 必存')
print('=' * 100)
