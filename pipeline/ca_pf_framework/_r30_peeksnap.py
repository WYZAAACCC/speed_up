#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r30_peeksnap.py —— 只读探针：列出算例快照/落盘文件里**到底存了什么**。

为什么需要它（用户明确要求）：
    「将仿真过程的全部数据保存在F盘下 …… 之后也能使用新的测量工具重新测量得到正确
     的结果，并且可以在原始数据上查错。」
⇒ 要判"能不能离线重算"，必须先把**落盘内容**逐 key 量出来（shape/dtype/nbytes），
   不能靠读代码或读文档猜（本仓库最贵的教训：文档说"有" ≠ 实际有）。

跑法：
    python3 _r30_peeksnap.py _exp/_bk_closed/dry_cl1b
    python3 _r30_peeksnap.py _exp/_bk_closed/dry_cl1b --csv
"""
import os
import sys
import glob
import numpy as np


def peek_npz(path):
    d = np.load(path, allow_pickle=True)
    tot = 0
    rows = []
    for k in d.files:
        a = d[k]
        try:
            nb = int(a.nbytes)
            rows.append((k, str(a.shape), str(a.dtype), nb))
            tot += nb
        except Exception:
            rows.append((k, repr(type(a)), '-', 0))
    return rows, tot


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = sys.argv[1]
    show_csv = '--csv' in sys.argv
    print('=' * 78)
    print('目录：%s' % root)
    print('=' * 78)
    for f in sorted(glob.glob(os.path.join(root, '*'))):
        bn = os.path.basename(f)
        sz = os.path.getsize(f)
        if f.endswith('.npz'):
            rows, tot = peek_npz(f)
            print('\n-- %s  文件 %.1f KB  解压后 %.2f MB' % (bn, sz / 1024.0, tot / 1048576.0))
            for k, sh, dt, nb in rows:
                print('     %-16s shape=%-22s dtype=%-10s %8.2f MB'
                      % (k, sh, dt, nb / 1048576.0))
        elif f.endswith('.csv') and show_csv:
            with open(f) as fh:
                lines = fh.readlines()
            print('\n-- %s  行数 %d（含表头）' % (bn, len(lines)))
            print('     表头：%s' % lines[0].strip())
            if len(lines) > 1:
                print('     第1行：%s' % lines[1].strip()[:200])
                print('     末行 ：%s' % lines[-1].strip()[:200])
            print('     步号列采样：%s' % ','.join(
                l.split(',')[0] for l in lines[1:8]))
        else:
            print('\n-- %-24s %8.1f KB' % (bn, sz / 1024.0))
            if f.endswith('.json'):
                with open(f) as fh:
                    txt = fh.read()
                print('     （json，%d 字符）%s' % (len(txt), txt[:160].replace('\n', ' ')))


if __name__ == '__main__':
    main()
