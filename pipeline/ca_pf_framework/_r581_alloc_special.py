#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_alloc_special.py --- 看清**特例**：带 `case` 的选择器脚本 + `EV="..."` 形式"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'


def main():
    sel, ev = [], []
    for dp, dn, fns in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in ('.git', '__pycache__')]
        for fn in fns:
            if not fn.endswith('.sh'):
                continue
            p = os.path.join(dp, fn)
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            if re.search(r'MMAP\)\s*echo', txt):
                sel.append(p)
            if re.search(r'EV="MALLOC', txt):
                ev.append(p)
    print('=' * 96)
    print('① 带 `case` 的"档位选择器"脚本：%d 个' % len(sel))
    print('=' * 96)
    for p in sel:
        print('  ── %s ──' % p)
        lines = open(p, encoding='utf-8', errors='replace').read().splitlines()
        for i, l in enumerate(lines, 1):
            if 'MALLOC' in l or 'case' in l or ';;' in l or 'esac' in l:
                print('   %4d| %s' % (i, l[:118]))
        print()
    print('=' * 96)
    print('② `EV="MALLOC..."` 形式：%d 个' % len(ev))
    print('=' * 96)
    for p in ev:
        print('  ── %s ──' % p)
        for i, l in enumerate(open(p, encoding='utf-8', errors='replace').read().splitlines(), 1):
            if 'MALLOC' in l:
                print('   %4d| %s' % (i, l[:118]))
        print()


if __name__ == '__main__':
    main()
