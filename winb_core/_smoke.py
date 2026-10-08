#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_smoke.py —— 最小冒烟：证明这个包**能完整跑起来**（不依赖源目录）。

跑一个小算例（N=32、20 步、单变体），检查：
  1) 引擎能构造；2) 能推进 20 步；3) 落盘 `series.csv` / `meta.json`；
  4) **没有** `JIT compile failed` / `ImportError` / `FileNotFoundError`。
⚠ 参数极小 ⇒ 只证明"能跑通"，**不用于任何物理结论**。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '_smoke_out')
PY = sys.executable

cmd = [PY, '-u', os.path.join(HERE, '_bk_exp.py'),
       '--N', '32', '--dx-nm', '62.5', '--steps', '20',
       '--every', '10', '--snap-every', '20', '--pair-every', '20',
       '--norm-smooth', '0', '--nthreads', '2', '--arm', 'dry',
       '--laths', '1', '--nuc-init', '0', '--nuc-every', '0',
       '--plate-L', '2000.0', '--plate-W', '2000.0', '--plate-T', '2000.0',
       '--facet-proj', '0', '--band-cells', '20',
       '--out', OUT, '--tag', 'smoke']

print('CMD: %s' % ' '.join(cmd))
os.makedirs(OUT, exist_ok=True)
log = os.path.join(OUT, 'smoke.log')
with open(log, 'w') as fh:
    rc = subprocess.call(cmd, cwd=HERE, stdout=fh, stderr=subprocess.STDOUT)
print('rc = %d   （日志 %s）' % (rc, log))

bad = ('JIT compile failed', 'ImportError', 'ModuleNotFoundError',
       'FileNotFoundError', 'Traceback')
txt = open(log, encoding='utf-8', errors='replace').read()
hits = [b for b in bad if b in txt]
print()
print('  `series.csv` 存在？ %s'
      % os.path.isfile(os.path.join(OUT, 'dry_smoke', 'series.csv')))
print('  `meta.json`  存在？ %s'
      % os.path.isfile(os.path.join(OUT, 'dry_smoke', 'meta.json')))
print('  可疑串： %s' % (hits if hits else '（无）'))
print()
ok = (rc == 0 and not hits
      and os.path.isfile(os.path.join(OUT, 'dry_smoke', 'series.csv')))
print('⇒ **%s**' % ('✅ 包可完整运行' if ok else '⛔ 有问题，见日志'))
sys.exit(0 if ok else 1)
