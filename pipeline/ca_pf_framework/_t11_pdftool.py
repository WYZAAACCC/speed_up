#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_pdftool.py —— ⓪ 检索前置：查本机有没有 PDF 转文本能力。
判据：打印每个候选库/可执行文件的可用性。不做任何假设。
"""
import os
import shutil
import subprocess
import sys

print("=== python:", sys.executable, sys.version.split()[0])

for mod in ("fitz", "pypdf", "PyPDF2", "pdfminer", "pdfplumber"):
    try:
        __import__(mod)
        print(f"[OK  ] import {mod}")
    except Exception as e:  # noqa: BLE001
        print(f"[MISS] import {mod}: {type(e).__name__}")

for exe in ("pdftotext", "pdfinfo", "pdftoppm", "mutool", "gs"):
    p = shutil.which(exe)
    print(f"[{'OK  ' if p else 'MISS'}] which {exe}: {p}")

# conda 环境
for cand in (
    "/root/miniconda3/envs/ml/bin/python",
    "/root/miniconda3/envs/moose/bin/python",
    "/root/miniconda3/bin/python",
):
    if os.path.exists(cand):
        r = subprocess.run(
            [cand, "-c", "import fitz;print('fitz',fitz.__version__)"],
            capture_output=True, text=True,
        )
        print(f"[ENV ] {cand}: rc={r.returncode} out={r.stdout.strip()!r} err={r.stderr.strip().splitlines()[-1:]!r}")
    else:
        print(f"[ENV ] {cand}: 不存在")
