#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_lit_r712_get.py —— 从 PDF 直接抽文本（只读），供 D-2 的率律检索。

优先目标（文件名片段）→ 为什么它最可能有"率律"：
  Kinetics-of-anomalous-multi-step-formation-of-lath-martensite   ← 标题就是 lath martensite 动力学
  Martensite-formation-kinetics-of-substitutional-Fe              ← 标题就是马氏体形成动力学
  Heating-induced-martensitic-transformation-and-time-dependent   ← 标题含 time-dependent
  Phase-field-simulation-framework-for-modeling-marten           ← 相场框架（可能给率式）
  Martensite-formation-in-titanium-alloys                         ← Ti 合金马氏体（同材料）
  Multiscale-modelling-of-mechanical-response-in-a-martensitic    ← 多尺度
  The-----transformation-in-Fe-and-Fe-Au-thin-films               ← α→γ 转变动力学
用法： cd /mnt/f/speed_up && /root/miniconda3/envs/ml/bin/python -u _lit_r712_get.py
"""
import io
import os
import re
import sys

SRC = '/mnt/f/参考论文/马氏体仿真'
OUT = '/mnt/f/speed_up/_litidx/lit_txt_r712'
os.makedirs(OUT, exist_ok=True)

KEYS = [
    'Kinetics-of-anomalous-multi-step-formation-of-lath-martens',
    'Martensite-formation-kinetics-of-substitutional-Fe',
    'Heating-induced-martensitic-transformation-and-time-dependent',
    'Phase-field-simulation-framework-for-modeling-marten',
    'Martensite-formation-in-titanium-alloys',
    'Multiscale-modelling-of-mechanical-response-in-a-martensitic',
    'The-----transformation-in-Fe-and-Fe-Au-thin-films',
]

pdfs = [f for f in os.listdir(SRC) if f.lower().endswith('.pdf')]
picked = []
for k in KEYS:
    for f in pdfs:
        if k.lower() in f.lower():
            picked.append((k, f))
            break


def extract(path):
    for eng in ('pdfminer', 'pypdf', 'PyPDF2', 'fitz', 'pdfplumber'):
        try:
            if eng == 'pdfminer':
                from pdfminer.high_level import extract_text
                return extract_text(path), eng
            if eng in ('pypdf', 'PyPDF2'):
                mod = __import__(eng)
                R = mod.PdfReader(path)
                return '\n'.join((p.extract_text() or '') for p in R.pages), eng
            if eng == 'fitz':
                import fitz
                d = fitz.open(path)
                return '\n'.join(pg.get_text() for pg in d), eng
            if eng == 'pdfplumber':
                import pdfplumber
                with pdfplumber.open(path) as d:
                    return '\n'.join((p.extract_text() or '') for p in d.pages), eng
        except Exception:
            continue
    return None, None


print('=' * 100)
for k, f in picked:
    p = os.path.join(SRC, f)
    txt, eng = extract(p)
    if txt is None:
        print('  ✗ 无法提取：%s' % f[:80])
        continue
    o = os.path.join(OUT, re.sub(r'[^\w.\-]', '_', f)[:110] + '.txt')
    io.open(o, 'w', encoding='utf-8').write(txt)
    n = len(txt.splitlines())
    print('  ✓ %-70s  引擎=%-9s 行=%d' % (f[:70], eng, n))
print('=' * 100)
print('输出目录：%s' % OUT)
sys.exit(0)
