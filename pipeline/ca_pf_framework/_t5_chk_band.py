#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t5_chk_band.py --- 验证 `--phi-band-every` 已与 `--snap-every` 对齐（s54 的改动）"""
import importlib.util as u
import sys

sys.argv = ['x']
s = u.spec_from_file_location('m', '_t5_short.py')
m = u.module_from_spec(s)
s.loader.exec_module(m)
for snap in ('40', '200'):
    a = m.ap.parse_args(['--tag', 'dry', '--snap-every', snap])
    c = m.build(a, [])
    i = c.index('--phi-band-every')
    ok = (c[i + 1] == snap)
    print('  --snap-every %-4s ⇒ --phi-band-every %-4s   %s'
          % (snap, c[i + 1], '✅ 对齐' if ok else '❌ 没对齐'))
print()
print('  ⇒ 判据② 的厚度量具分辨率 = `--phi-band-every` = `--snap-every`')
print('     旧：200 步（写死）；新：跟随 snap-every ⇒ 默认 40 步（**5× 提升**）')
