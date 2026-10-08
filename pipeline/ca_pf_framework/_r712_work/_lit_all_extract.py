#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_all_extract.py —— 把 F:\\参考论文\\马氏体仿真 下**全部** PDF 抽文本（只读）。

断点续跑：已存在的 .txt 跳过。
输出： /mnt/f/speed_up/_litidx/lit_txt_all/
用法： cd /mnt/f/speed_up && /root/miniconda3/envs/ml/bin/python -u _lit_all_extract.py
"""
import io
import os
import re
import sys
import time

SRC = '/mnt/f/参考论文/马氏体仿真'
OUT = '/mnt/f/speed_up/_litidx/lit_txt_all'
os.makedirs(OUT, exist_ok=True)


def safe(f):
    return re.sub(r'[^\w.\-]', '_', f)[:150]


def extract(path):
    try:
        import pypdf
        R = pypdf.PdfReader(path)
        if len(R.pages) > 60:          # 太长的（书/综述）也抽，但记录页数
            pass
        return '\n'.join((p.extract_text() or '') for p in R.pages), 'pypdf'
    except Exception as e:
        return None, 'pypdf-fail:%s' % type(e).__name__


pdfs = sorted(f for f in os.listdir(SRC) if f.lower().endswith('.pdf'))
print('PDF 总数 = %d' % len(pdfs))
done = skip = fail = 0
t0 = time.time()
for i, f in enumerate(pdfs, 1):
    o = os.path.join(OUT, safe(f) + '.txt')
    if os.path.exists(o) and os.path.getsize(o) > 200:
        skip += 1
        continue
    txt, eng = extract(os.path.join(SRC, f))
    if txt is None or len(txt) < 200:
        fail += 1
        print('  ✗ [%3d/%3d] %-70s %s' % (i, len(pdfs), f[:70], eng))
        continue
    io.open(o, 'w', encoding='utf-8').write(txt)
    done += 1
    if i % 20 == 0:
        print('  … [%3d/%3d] 新抽 %d / 跳过 %d / 失败 %d  (%.0f s)'
              % (i, len(pdfs), done, skip, fail, time.time() - t0), flush=True)
print('=' * 90)
print('完成：新抽 %d，跳过 %d，失败 %d，用时 %.0f s' % (done, skip, fail, time.time() - t0))
tot = sum(os.path.getsize(os.path.join(OUT, x)) for x in os.listdir(OUT))
print('输出目录 %s ：%d 个 txt，合计 %.1f MB'
      % (OUT, len(os.listdir(OUT)), tot / 1e6))
sys.exit(0)
