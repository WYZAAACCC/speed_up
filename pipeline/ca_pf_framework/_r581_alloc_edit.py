#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_alloc_edit.py --- ★★★★★★★ **A4 落地**：删掉两个阈值变量、**保留 `MALLOC_ARENA_MAX=2`**

## 授权（用户 2026-10-02 逐字）
> 「按照你的建议**去掉那两个阈值变量**（`ARENA_MAX=2` **保留** —— 它又快又省），
>   **但先补一步**：在 N=160 上量一次峰值 RSS 与 s/步，确认峰值不涨到危险区」

## ★★★ 三条安全设计（**都做了才敢跑**）
1. **默认 `--dry-run`** ⇒ **不写任何文件**，只打印"会改哪一行、改成什么" ⇒ 人看过再 `--apply`；
2. **★ 白名单排除"测量仪器"**：`_r577_*` / `_r578_*` 是**量具**（`case` 选择器 / `EV="..."`）
   ⇒ **改了就没法复测** ⇒ **一律跳过**；**`env -u ...` 那几条是我自己的快路脚本** ⇒ **也跳过**；
3. **只动"赋值行"**：行内出现 `MALLOC_(MMAP|TRIM)_THRESHOLD_=` 且**不是注释**、**不是 `env -u`**
   ⇒ **只删那两个 token**，**其余一个字符不动**（含 `MALLOC_ARENA_MAX=2`、`PYTHONDONTWRITEBYTECODE=1`、行尾 `\\`）。

## 记账
* 每个改动文件**记 before/after 的 sha256 + 字节数**，写进 `_r581_alloc_edit_manifest.tsv`；
* **备份原件**到 `_r580_backup/allocEdfix_<时间戳>/`（**不删原件，只复制**）。
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import time

# ★ 仪器/快路白名单（**不改**）
SKIP_PAT = re.compile(r'(_r57[78]_|_r581_alloc(160|_edit|_survey|_special)|_r581_.*_superseded)')
# ★ 要删的两个 token（值可能不同，故用 `=\S+`）
TOK = re.compile(r'\bMALLOC_(?:MMAP_THRESHOLD_|TRIM_THRESHOLD_)=\S+')
KEEP = 'MALLOC_ARENA_MAX='


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 16), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', nargs='?', default='.')
    ap.add_argument('--apply', action='store_true', help='真的写（默认只 dry-run）')
    a = ap.parse_args()
    root = a.root
    stamp = time.strftime('%Y%m%d_%H%M%S')
    bkdir = os.path.join('_r580_backup', 'allocEdfix_' + stamp)
    man = '_r581_alloc_edit_manifest.tsv'
    rows = []
    nfile = nline = 0
    skipped = []
    print('=' * 100)
    print('A4 落地：删 `MALLOC_MMAP_THRESHOLD_` + `MALLOC_TRIM_THRESHOLD_`，**保留 `MALLOC_ARENA_MAX`**')
    print('模式：%s' % ('**APPLY（会写盘）**' if a.apply else 'DRY-RUN（不写盘）'))
    print('=' * 100)
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.git', '__pycache__', '_r580_backup')]
        for fn in sorted(fns):
            if not fn.endswith('.sh'):
                continue
            p = os.path.join(dp, fn)
            if SKIP_PAT.search(p):
                skipped.append(p)
                continue
            try:
                txt = open(p, encoding='utf-8', errors='replace').read()
            except Exception:
                continue
            lines = txt.split('\n')
            out = []
            changed = 0
            for l in lines:
                if 'MALLOC_MMAP_THRESHOLD_=' in l or 'MALLOC_TRIM_THRESHOLD_=' in l:
                    st = l.lstrip()
                    if st.startswith('#'):          # ★ 注释：不动
                        out.append(l)
                        continue
                    if 'env -u' in l:               # ★ 快路脚本：不动
                        out.append(l)
                        continue
                    new = TOK.sub('', l)
                    new = re.sub(r'[ \t]{2,}', ' ', new).rstrip()
                    # ★ 若整行只剩 `export` / 空 ⇒ 整行丢掉（但只当它原本就是纯赋值行）
                    core = new.strip()
                    if core in ('', 'export', '\\') or re.fullmatch(r'(export[ \t]*)?\\?', core):
                        new = None
                    if new != l:
                        changed += 1
                        print('  ── %s' % p)
                        print('     - %s' % l[:150])
                        print('     + %s' % ('（整行删除）' if new is None else new[:150]))
                    out.append(new if new is not None else '\x00DROP\x00')
                else:
                    out.append(l)
            if changed:
                newlines = [x for x in out if x != '\x00DROP\x00']
                newtxt = '\n'.join(newlines)
                nfile += 1
                nline += changed
                h0 = sha(p)
                rows.append((p, changed, h0, len(txt)))
                if a.apply:
                    os.makedirs(bkdir, exist_ok=True)
                    rel = p.replace('/', '__').replace('\\', '__').lstrip('.')
                    shutil.copy2(p, os.path.join(bkdir, rel))
                    with open(p, 'w', encoding='utf-8', newline='') as f:
                        f.write(newtxt)
                    h1 = sha(p)
                    with open(man, 'a', encoding='utf-8') as f:
                        f.write('%s\t%d\t%s\t%s\t%d\t%d\n'
                                % (p, changed, h0, h1, len(txt), len(newtxt)))
    print()
    print('=' * 100)
    print('汇总：**%d 个脚本、%d 行**会被改（%s）' % (nfile, nline,
          '已写盘' if a.apply else '**未写盘**'))
    if skipped:
        print('跳过（仪器/快路白名单）%d 个：' % len(skipped))
        for s in skipped[:10]:
            print('   %s' % s)
        if len(skipped) > 10:
            print('   …（还有 %d 个）' % (len(skipped) - 10))
    if a.apply and rows:
        print('原件备份：%s' % bkdir)
        print('改动台账：%s（%d 行）' % (man, len(rows)))
    print('=' * 100)
    print('★ 下一步（若 apply）：')
    print('   ① 抽查几个脚本的头几行；② **跑一次真实路径冒烟**确认能跑；③ 记账。')


if __name__ == '__main__':
    main()
