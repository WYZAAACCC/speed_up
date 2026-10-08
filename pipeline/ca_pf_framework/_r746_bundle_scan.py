#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r746_bundle_scan.py —— **只读扫描**：算出"最小可运行主仿真集"= 闭包 + 数据依赖。

## 为什么要扫数据依赖
上一轮已实测闭包 = 20 个模块 / 19,428 行。但闭包**不自包含**：
驱动会读外部文件（热历史、变体表、`irf` 等）。只抄 `.py` 会**跑不起来**。

## 三条扫描
1. **`ast` 传递闭包**（从入口 `_bk_exp.py`），输出每个模块的行数与 SHA256；
2. **文件 I/O 扫描**：在闭包内文件里找 `open(` / `np.load(` / `np.loadtxt(` /
   `genfromtxt(` / `read_csv(` / `to_csv(` / `json.load(` / `.npz` / `.csv` / `.json`
   的**字面量路径**，标出哪些是**读**（= 外部依赖）；
3. **盘上实际存在的数据文件**清单（`.csv/.json/.npz/.txt/.dat`），
   与第 2 步求交 ⇒ 得出**必须一起搬**的清单。

⚠ **本脚本只读，不复制也不删任何东西。**
"""
import ast
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = sys.argv[1] if len(sys.argv) > 1 else '_bk_exp.py'
PY_EXT = ('npz', 'npy', 'csv', 'json', 'txt', 'dat', 'e', 'xdmf', 'vtr')


def imports_of(path):
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


def closure(entry):
    allpy = {f[:-3] for f in os.listdir(HERE) if f.endswith('.py')}
    seen, stack = set(), [entry[:-3]]
    while stack:
        m = stack.pop()
        if m in seen or m not in allpy:
            continue
        seen.add(m)
        stack += list(imports_of(os.path.join(HERE, m + '.py')))
    return sorted(seen)


PAT = re.compile(
    r"""(?:open|np\.load|np\.loadtxt|np\.genfromtxt|np\.savez\w*|pd\.read_csv"""
    r"""|json\.load|json\.dump|np\.save|np\.savetxt)\s*\(\s*"""
    r"""['"]([^'"]+)['"]""")
LIT = re.compile(r"""['"]([A-Za-z0-9_./\-]+\.(?:%s))['"]""" % '|'.join(PY_EXT))


def main():
    mods = closure(ENTRY)
    print('=' * 88)
    print('最小可运行主仿真集 —— 扫描结果（入口 %s）' % ENTRY)
    print('=' * 88)
    print('  闭包模块数 = %d' % len(mods))
    tot = 0
    print()
    print('  %-34s %7s %10s  %s' % ('模块', '行数', '字节', 'sha256[:12]'))
    for m in sorted(mods):
        p = os.path.join(HERE, m + '.py')
        b = open(p, 'rb').read()
        n = b.decode('utf-8', 'replace').splitlines()
        h = hashlib.sha256(b).hexdigest()[:12]
        tot += len(n)
        print('  %-34s %7d %10d  %s' % (m + '.py', len(n), len(b), h))
    print('  ' + '-' * 70)
    print('  %-34s %7d' % ('★ 合计', tot))

    # ---- 文件 I/O 与字面量路径 ----
    reads, writes, lits = {}, {}, {}
    for m in mods:
        p = os.path.join(HERE, m + '.py')
        txt = open(p, encoding='utf-8', errors='replace').read()
        for mt in PAT.finditer(txt):
            s = mt.group(0)
            tgt = mt.group(1)
            (writes if ('save' in s or 'dump' in s or 'to_csv' in s)
             else reads).setdefault(tgt, set()).add(m + '.py')
        for mt in LIT.finditer(txt):
            lits.setdefault(mt.group(1), set()).add(m + '.py')

    def dump(title, d):
        print()
        print('  ## %s' % title)
        if not d:
            print('     （无）')
            return
        for k in sorted(d):
            ex = '✅存在' if os.path.exists(os.path.join(HERE, k)) else '⛔缺'
            print('     %-42s [%s]  ← %s' % (k[:42], ex, ', '.join(sorted(d[k]))[:48]))

    dump('【读】外部数据依赖（必须一起搬）', reads)
    dump('【写】输出路径（跑起来会生成，不必搬）', writes)

    # 引用了"形如数据文件"的字面量但没被 open 抓到
    extra = {k: v for k, v in lits.items() if k not in reads and k not in writes}
    dump('【其它字面量数据文件名】（可能是默认值/提示串，需人工判）', extra)

    # ---- 盘上实际数据文件 ----
    print()
    print('  ## 本目录盘上的数据文件（供对照）')
    for ext in PY_EXT:
        fs = [f for f in os.listdir(HERE) if f.endswith('.' + ext)]
        if fs:
            print('     .%-5s %3d 个：%s' % (ext, len(fs),
                                          ', '.join(sorted(fs)[:6])
                                          + (' …' if len(fs) > 6 else '')))
    print()
    print('  ⚠ 本脚本只读；未复制、未删除。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
