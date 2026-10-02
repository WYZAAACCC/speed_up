#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_alloc_survey.py --- ★★★★★ **改动前的摸底**：134 个脚本里那三个变量**到底怎么写**的

## 为什么必须先摸底
**不同的写法要用不同的改法**（**P28：改调用点前整段读完**）：
* 三个在**同一行** ⇒ 要**只删两段、留 `ARENA_MAX=2`**；
* 分成**两三行** ⇒ 逐行删；
* 有的可能**带注释**、**带 `&&`**、或在 `if` 里 ⇒ **都不能正则一刀切**。
**⇒ 本脚本只**读**、只**分类**，**不写**。**
"""
import os
import re
import sys
from collections import Counter

ROOT = sys.argv[1] if len(sys.argv) > 1 else '.'
PAT = re.compile(r'^[ \t]*(?:export[ \t]+)?(.*MALLOC_(?:MMAP_THRESHOLD_|TRIM_THRESHOLD_|ARENA_MAX).*)$',
                 re.M)


def main():
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in ('.git', '__pycache__')]
        for fn in filenames:
            if not fn.endswith('.sh'):
                continue
            p = os.path.join(dirpath, fn)
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            ms = PAT.findall(txt)
            if ms:
                hits.append((p, ms))
    print('=' * 100)
    print('MALLOC 变量的摸底：找到 **%d 个 .sh 脚本**' % len(hits))
    print('=' * 100)
    forms = Counter()
    for p, ms in hits:
        for m in ms:
            forms[m.strip()] += 1
    print()
    print('  ── **出现的写法**（按次数降序，共 %d 种）──' % len(forms))
    for m, n in forms.most_common(20):
        print('   %4d×  %s' % (n, m[:150]))
    print()
    # 分类
    cat = Counter()
    for p, ms in hits:
        joined = ' | '.join(x.strip() for x in ms)
        has_mmap = 'MMAP_THRESHOLD' in joined
        has_trim = 'TRIM_THRESHOLD' in joined
        has_arena = 'ARENA_MAX' in joined
        same = len(ms) == 1
        cat[(has_mmap, has_trim, has_arena, same)] += 1
    print('  ── 分类（mmap / trim / arena / 是否同一行）──')
    for k, n in cat.most_common():
        print('   mmap=%-5s trim=%-5s arena=%-5s 同一行=%-5s ⇒ **%d 个脚本**' % (*k, n))
    print()
    print('  ── 每个脚本的原文（前 25 个）──')
    for p, ms in hits[:25]:
        print('   %s' % os.path.relpath(p, ROOT))
        for m in ms:
            print('       %s' % m.strip()[:140])
    if len(hits) > 25:
        print('   …（还有 %d 个）' % (len(hits) - 25))
    print('=' * 100)


if __name__ == '__main__':
    main()
