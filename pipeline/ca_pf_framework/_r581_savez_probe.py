#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_savez_probe.py --- ★★★★★ **实测** numpy 的 `savez*` 文件名行为

## 为什么要先实测（P21/P20 的纪律）
功能测试报的错是：
```
[Errno 2] No such file or directory: '...ckpt_A.npz.tmp' -> '...ckpt_A.npz'
```
**⇒ 源文件不存在** ⇒ 怀疑 `np.savez_compressed('x.npz.tmp', ...)` **自己补了 `.npz`**
⇒ **不许靠记忆下结论**，这里**实测四种写法**。
"""
import os
import tempfile

import numpy as np

d = tempfile.mkdtemp()
print('=' * 88)
print('实测：`np.savez_compressed` 的文件名行为（临时目录 %s）' % os.path.basename(d))
print('=' * 88)

CASES = [
    ('传路径 "a.npz"',        os.path.join(d, 'a.npz')),
    ('传路径 "b.npz.tmp"',    os.path.join(d, 'b.npz.tmp')),
    ('传路径 "c.tmp"',        os.path.join(d, 'c.tmp')),
    ('传**文件对象** "d.tmp"', None),
]
for name, p in CASES:
    before = set(os.listdir(d))
    if p is None:
        p2 = os.path.join(d, 'd.tmp')
        with open(p2, 'wb') as fh:
            np.savez_compressed(fh, y=np.zeros(4))
    else:
        np.savez_compressed(p, y=np.zeros(4))
    after = set(os.listdir(d))
    new = sorted(after - before)
    print('  %-24s ⇒ 实际新增：%s' % (name, new))
print()
print('  ── 判读 ──')
print('   · **要给自定义扩展名（如 `.tmp`）⇒ 必须传**文件对象****（numpy 不会改文件对象的名字）')
print('   · 传**路径**时，numpy 见结尾不是 `.npz` 就**自己补** ⇒ 原子写的"源"就不存在了')
print('=' * 88)
