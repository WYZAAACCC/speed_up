#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_bk_meta.py —— 打印若干算例目录的 `meta.json`（扁平化）。

用法: python3 _bk_meta.py <目录或 series.csv 所在目录> [...]
     python3 _bk_meta.py --list <root>      # 列出 root 下所有臂 + 是否有 meta/series/快照

★ 存在的理由：在 PowerShell 里写 `wsl -e bash -lc "... python -c \"def walk...\" ..."`
会被 PowerShell 的解析器搅碎（引号/括号）。一律落地成文件跑。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def walk(d, p=''):
    for k in sorted(d):
        v = d[k]
        if isinstance(v, dict):
            walk(v, p + k + '.')
        else:
            print('  %-38s = %s' % (p + k, repr(v)[:120]))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == '--list':
        root = args[1]
        if not os.path.isabs(root):
            root = os.path.join(HERE, root)
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            ns = len([f for f in os.listdir(d) if f.startswith('snap_')])
            mp = os.path.join(d, 'meta.json')
            tag = ''
            if os.path.exists(mp):
                try:
                    m = json.load(open(mp, encoding='utf-8'))
                    # ★ meta.json 的参数在**顶层**（不是 exp 子字典）
                    tag = ('N=%s steps=%s tag=%s arm=%s nv=%s dt=%s'
                           % (m.get('N'), m.get('steps'), m.get('tag'),
                              m.get('arm'), m.get('nv'), m.get('reinit_dt')))
                except Exception as ex:
                    tag = 'meta 读不出: %s' % ex
            print('  %-26s snaps=%-3d %s' % (name, ns, tag))
        return 0
    for d in args:
        if not os.path.isabs(d):
            d = os.path.join(HERE, d)
        print('=' * 100)
        print(d)
        mp = os.path.join(d, 'meta.json')
        if not os.path.exists(mp):
            print('  **没有 meta.json**')
            continue
        walk(json.load(open(mp, encoding='utf-8')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
