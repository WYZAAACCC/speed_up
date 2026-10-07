#!/usr/bin/env python3
"""R52 正对照（P1-30 的修复）：**块心间距必须精确等于 `--block-gap-nm`**。

已知答案（可独立算出来）：
  修复后 `_cb = c0 ± 0.5·gap·u` ⇒ 两块心距 **恒等于 gap**，与长轴夹角无关。
  旧代码给出 `gap·|a_0 + a_1|/2` ⇒ 反平行时 ≈ 0。

判据（预先写死）：
  J-0a 日志里两块心的**坐标差**模长 ≈ `--block-gap-nm`（±2%）
  J-0b **实测**（从落盘 `region` 量两块合并包围盒的中心距）≈ gap（±10%）
  J-0c `nf2(t=0) == 0`
"""
import re
import subprocess
import sys

import numpy as np

sys.path.insert(0, '/mnt/f/speed_up/pipeline/ca_pf_framework')
import os
os.chdir('/mnt/f/speed_up/pipeline/ca_pf_framework')


def centres_from_log(tag):
    """从运行日志里抓两行 `块N：… 块心=[x y z] µm`。"""
    import glob
    fs = sorted(glob.glob('_w2_*%s*.log' % tag), key=os.path.getmtime)
    txt = open(fs[-1], encoding='utf-8', errors='replace').read()
    cs = []
    for m in re.finditer(r'块心=\[\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\]', txt):
        cs.append([float(m.group(i)) for i in (1, 2, 3)])
    return cs, fs[-1]


def centres_from_region(tag):
    import glob
    d = '_exp/_bk_mb/dry_%s' % tag
    snaps = sorted(glob.glob(os.path.join(d, 'snap_*.npz')))
    if not snaps:
        return None, None
    z = np.load(snaps[0])
    reg, N, L = z['region'], int(z['N']), float(z['L'])
    dx = L / N
    vm = {int(a): int(b) for a, b in zip(z['vmap_keys'], z['vmap_vals'])}
    out = {}
    for k, v in vm.items():
        m = (reg == k)
        if m.any():
            out.setdefault(v, []).append(np.argwhere(m))
    cen = {}
    for v, arrs in out.items():
        idx = np.vstack(arrs)
        cen[v] = idx.mean(0) * dx * 1e9
    vs = sorted(cen)
    if len(vs) < 2:
        return None, None
    return float(np.linalg.norm(cen[vs[0]] - cen[vs[1]])), cen


tag = sys.argv[1] if len(sys.argv) > 1 else 'b62r'
gap = float(sys.argv[2]) if len(sys.argv) > 2 else 3000.0
print('=== 臂 %s   请求 gap = %.0f nm' % (tag, gap))
cs, logf = centres_from_log(tag)
print('日志: %s' % logf)
if len(cs) >= 2:
    d = float(np.linalg.norm(np.array(cs[0]) - np.array(cs[1]))) * 1000.0
    print('  J-0a 日志块心距 = %.0f nm   (请求 %.0f)  ⇒ %s'
          % (d, gap, 'PASS' if abs(d - gap) <= 0.02 * gap else 'FAIL'))
else:
    print('  J-0a 日志里没抓到两块心（找到 %d 个）' % len(cs))
dr, cen = centres_from_region(tag)
if dr is not None:
    print('  J-0b 实测块质心距 = %.0f nm   (请求 %.0f)  ⇒ %s'
          % (dr, gap, 'PASS' if abs(dr - gap) <= 0.10 * gap else 'FAIL'))
else:
    print('  J-0b 还没有快照')
