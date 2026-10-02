#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_r581_ckpt_keysize.py --- ★★★★★ **逐键**量检查点的压缩后体积（找出成本大头）

## 为什么要逐键
功能测试实测：N=64 的检查点 **21 MB/帧**，而同一台机器上 `--phi-every 1` 的快照只有 **4.9 MB**
—— **两者都存了 `g.phi`（482 MB 原始）** ⇒ **差异不在 φ**。
**⇒ 必须逐键量，才能知道 N=160 的真实成本该按谁外推**（不许拍脑袋）。
"""
import os
import sys
import tempfile

import numpy as np

p = sys.argv[1] if len(sys.argv) > 1 else None
if p is None or not os.path.exists(p):
    print('  ⚠ 用法：_r581_ckpt_keysize.py <ckpt.npz>')
    raise SystemExit(1)
z = np.load(p, allow_pickle=False)
print('=' * 100)
print('逐键体积：%s（文件 %.2f MB）' % (os.path.basename(p), os.path.getsize(p) / 1048576.0))
print('=' * 100)
rows = []
tmpd = tempfile.mkdtemp()
for k in sorted(z.files):
    a = z[k]
    raw = a.nbytes
    q = os.path.join(tmpd, 'one.npz')
    with open(q, 'wb') as fh:
        np.savez_compressed(fh, **{k: a})
    comp = os.path.getsize(q)
    os.remove(q)
    rows.append((comp, k, raw, a.shape, a.dtype))
rows.sort(reverse=True)
print('  %-20s %-22s %-10s %10s %10s %7s' %
      ('键', '形状', 'dtype', '原始(MB)', '压缩(MB)', '压缩比'))
print('  ' + '-' * 94)
tot_c = tot_r = 0
for comp, k, raw, shp, dt in rows:
    tot_c += comp
    tot_r += raw
    if comp < 1024 and raw < 1024:
        continue
    print('  %-20s %-22s %-10s %10.2f %10.2f %7.1fx' %
          (k, str(shp)[:22], str(dt), raw / 1048576.0, comp / 1048576.0,
           (raw / max(comp, 1)) if raw else 0))
print('  ' + '-' * 94)
print('  %-20s %-22s %-10s %10.2f %10.2f %7.1fx' %
      ('**合计**', '', '', tot_r / 1048576.0, tot_c / 1048576.0,
       tot_r / max(tot_c, 1)))
print('  （逐键压缩之和 %.2f MB vs 整文件 %.2f MB ⇒ 差 %.2f MB 是 zip 头/共享开销）'
      % (tot_c / 1048576.0, os.path.getsize(p) / 1048576.0,
         (os.path.getsize(p) - tot_c) / 1048576.0))
print()
print('  ★ 读法：**占比最大的那一项**就是成本大头 ⇒ N=160 的外推按它缩放')
print('     若大头是 `phi`（光滑 SDF，压得好）⇒ 按活跃场数外推；')
print('     若是 `pf_eps0_lag` 之类**应变场**（界面尖锐、压不动）⇒ 按 N³ 外推，不能按活跃场数')
print('=' * 100)
