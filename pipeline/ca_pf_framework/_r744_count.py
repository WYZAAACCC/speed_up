#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r744_count.py —— **主仿真代码到底多少行**：从入口做**传递闭包**，再分行计数。

## 为什么要脚本算而不是数
本目录有 **1737 个 .py**（含几百个一次性探针 `_fix_*`/`_diag_*`/`_patch_*`），
手工列的清单会**混进非依赖项**（已实测：`windowB_hybrid.py`/`windowB_rve3d.py`/
`windowB_gibbs_rve.py` 都不在闭包里）。
⇒ 用 `ast` 解析 import，从入口 `_bk_exp.py` 做 BFS。

## 口径
* **入口**：`_bk_exp.py`（生产驱动；`--laths`/`--tag`/`--out` 那一套）
* **入栈条件**：import 的模块名**在本目录存在同名 .py**（排除标准库/第三方）
* **`import X` 里 `X` 是包名**（如 `numpy`）⇒ 本目录无同名 `.py` ⇒ 自动排除
* 只算 `.py`；行数按 `splitlines()`（**与 `wc -l` 同口径**）
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = sys.argv[1] if len(sys.argv) > 1 else '_bk_exp.py'


def local_mods(path):
    """返回该文件 import 的、且本目录有同名 .py 的模块名。"""
    try:
        src = open(path, encoding='utf-8', errors='replace').read()
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return []
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                out.add(al.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                out.add(node.module.split('.')[0])
    return sorted(out)


def main():
    allpy = {f[:-3] for f in os.listdir(HERE) if f.endswith('.py')}
    seen, order, missing = set(), [], set()
    stack = [ENTRY[:-3]]
    while stack:
        m = stack.pop()
        if m in seen or m not in allpy:
            continue
        seen.add(m)
        order.append(m)
        for dep in local_mods(os.path.join(HERE, m + '.py')):
            if dep in allpy:
                stack.append(dep)
            else:
                missing.add(dep)

    rows = []
    for m in sorted(order):
        p = os.path.join(HERE, m + '.py')
        n = len(open(p, encoding='utf-8', errors='replace').read().splitlines())
        rows.append((n, m))
    rows.sort(reverse=True)
    print('=' * 84)
    print('主仿真代码：从入口 `%s` 做传递闭包' % ENTRY)
    print('=' * 84)
    print('  %-34s %8s %10s' % ('模块', '行数', '字节'))
    tot = byt = 0
    for n, m in rows:
        b = os.path.getsize(os.path.join(HERE, m + '.py'))
        tot += n
        byt += b
        print('  %-34s %8d %10d' % (m + '.py', n, b))
    print('  ' + '-' * 54)
    print('  %-34s %8d %10d' % ('★ 合计（%d 个模块）' % len(rows), tot, byt))
    print()
    print('  参考：本目录 .py 总数 = %d' % len(allpy))
    print('  ⇒ 闭包占 %.1f%%（其余是一次性探针/验证脚本）' % (100.0 * len(rows) / len(allpy)))
    if missing:
        print()
        print('  （非本目录的 import，已排除：%s）'
              % ', '.join(sorted(missing)[:14]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
