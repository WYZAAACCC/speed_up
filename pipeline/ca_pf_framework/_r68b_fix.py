#!/usr/bin/env python3
"""R68b: 修 `_r68_facet_op.py` 的自检打印过滤（`hs` → `lo/hi`），然后跑自检。"""
import os
import subprocess

os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')
p = '_r68_facet_op.py'
s = open(p, encoding='utf-8').read()
s = s.replace("if k != 'hs'}", "if k not in ('lo', 'hi')}")
open(p, 'w', encoding='utf-8').write(s)
print('patched:', "if k not in ('lo', 'hi')}" in s)
r = subprocess.run(['/root/miniconda3/envs/ml/bin/python', p],
                   capture_output=True, text=True)
print(r.stdout[-1500:])
print(r.stderr[-600:])
