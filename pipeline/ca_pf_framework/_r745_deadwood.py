#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r745_deadwood.py —— **实测**：哪些 .py 是本仓的"活代码"，哪些是死木。

## 判活的三条通路（**任一命中即算活**）
| # | 通路 | 怎么查 |
|---|---|---|
| **1** | **依赖闭包** | 从入口（`_bk_exp.py` / `main()` 类）用 `ast` 做传递闭包 |
| **2** | **被 `.sh` 调用** | 在全部 `.sh` 里搜文件名 |
| **3** | **被 `.md` 点名引用** | 在全部 `.md` 里搜 `xxx.py`（**证据链** —— 报告里"每个数字可溯源"靠它）|
| **4** | **被其它 `.py` import** | `ast` 扫全部 `.py` 的 import |

## 输出
* 分组：闭包内 / 仅被 sh / 仅被 md / 仅被 py-import / **完全无引用**
* 每组给**文件数与行数**，并列出"完全无引用"组的**完整清单**（供人工确认）

⚠ **本脚本只读，不删任何东西。**
"""
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRIES = ['_bk_exp.py']          # 生产入口；可加更多

py = sorted(f for f in os.listdir(HERE) if f.endswith('.py'))
py_set = {f[:-3] for f in py}


def ast_imports(path):
    try:
        tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    except (OSError, SyntaxError):
        return set()
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            out.add(n.module.split('.')[0])
    return out


def main():
    # 1) 闭包
    closure, stack = set(), [e[:-3] for e in ENTRIES]
    while stack:
        m = stack.pop()
        if m in closure or m not in py_set:
            continue
        closure.add(m)
        stack += list(ast_imports(os.path.join(HERE, m + '.py')))

    # 2) 被 import（任何 .py）
    imported_by = {}
    for f in py:
        for d in ast_imports(os.path.join(HERE, f)):
            if d in py_set:
                imported_by.setdefault(d, set()).add(f)

    # 3) 被 .sh 调用
    sh_txt = ''
    for f in os.listdir(HERE):
        if f.endswith('.sh'):
            sh_txt += open(os.path.join(HERE, f), encoding='utf-8',
                           errors='replace').read()

    # 4) 被 .md 点名
    md_txt = ''
    for f in os.listdir(HERE):
        if f.endswith('.md'):
            md_txt += open(os.path.join(HERE, f), encoding='utf-8',
                           errors='replace').read()

    groups = {'闭包': [], '仅被 import': [], '仅被 sh': [], '仅被 md':
              [], '无引用': []}
    for f in py:
        base = f[:-3]
        in_closure = base in closure
        in_sh = re.search(r'\b%s\.py\b' % re.escape(f), sh_txt) is not None
        in_md = re.search(r'\b%s\.py\b' % re.escape(f), md_txt) is not None
        in_imp = base in imported_by
        if in_closure:
            g = '闭包'
        elif in_imp:
            g = '仅被 import'
        elif in_sh:
            g = '仅被 sh'
        elif in_md:
            g = '仅被 md'
        else:
            g = '无引用'
        groups[g].append(f)

    def lines(fs):
        t = 0
        for f in fs:
            t += len(open(os.path.join(HERE, f), encoding='utf-8',
                          errors='replace').read().splitlines())
        return t

    print('=' * 84)
    print('死木实测（**只读；本脚本不删任何东西**）')
    print('=' * 84)
    print('  本目录 .py 总数 = %d' % len(py))
    print()
    print('  %-12s %6s %10s   %s' % ('组', '文件数', '行数', '含义'))
    meaning = {
        '闭包': '★ 主仿真依赖闭包（入口 %s）' % ', '.join(ENTRIES),
        '仅被 import': '被其它 .py import（含探针/验证）',
        '仅被 sh': '只被 .sh 调用',
        '仅被 md': '只在文档里被点名（**证据链**）',
        '无引用': '⚠ **既不在闭包、也没被 sh/md/py 引用**',
    }
    for g in ('闭包', '仅被 import', '仅被 sh', '仅被 md', '无引用'):
        print('  %-12s %6d %10d   %s' % (g, len(groups[g]), lines(groups[g]),
                                         meaning[g]))
    tot = sum(len(v) for v in groups.values())
    print('  %-12s %6d %10d' % ('合计', tot, lines(py)))
    print()
    print('  ⇒ **"无引用"组占 %.1f%%（%d 个文件 / %d 行）**'
          % (100.0 * len(groups['无引用']) / len(py), len(groups['无引用']),
             lines(groups['无引用'])))
    print()
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        print('=' * 84)
        print('"无引用"组完整清单（供人工确认；**不自动删**）')
        print('=' * 84)
        for f in groups['无引用']:
            print('  %s' % f)
    else:
        print('  （加 `--list` 参数可打印"无引用"组完整清单）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
