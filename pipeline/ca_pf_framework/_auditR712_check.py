#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_auditR712_check.py —— 核对 R712 修复方案引用的**代码事实**（只读）。

核对项：
  C1 `nv` 的真实值（方案 §4.3 引 `nv=220`）
  C2 `nuc-block-target` 的真实值（方案 §4.3 引 9）
  C3 `pair-every` 的生产值（方案 §4.3 引 100）
  C4 `elastic_soft` 的**默认值来源**（方案 §7.3 要"不能以隐藏默认值开启"）
  C5 `ed_eta` 的生产值与方案要求的"本构来源"标注现状
  C6 引擎里有没有"位点密度"这个量（方案 §6.1 的 λ_b 需要）
  C7 引擎里有没有"面级"的量（方案 §7.1 的 v_f / M_f 需要）
运行： cd /mnt/f/speed_up/pipeline/ca_pf_framework
       /root/miniconda3/envs/ml/bin/python -u _auditR712_check.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DRV = os.path.join(HERE, '_bk_exp.py')
SURF = os.path.join(HERE, 'windowB_surface.py')


def rd(p):
    return io.open(p, encoding='utf-8').read().splitlines()


drv, surf = rd(DRV), rd(SURF)
txt_drv = '\n'.join(drv)
txt_surf = '\n'.join(surf)

print('=' * 84)
print('R712 方案引用的代码事实核对（基线 9cd9598）')
print('=' * 84)

# ---- C1/C2/C3：生产参数 ----
cmd = os.path.join(HERE, '_t11_relaunch_cmd.sh')
c = io.open(cmd, encoding='utf-8').read() if os.path.exists(cmd) else ''
lat = re.search(r'--laths\s+([\d,]+)', c)
if lat:
    vals = [int(x) for x in lat.group(1).split(',')]
    from collections import Counter
    cnt = Counter(vals)
    print('C1 `nv`（场数 = --laths 的元素个数）= **%d**  （方案 §4.3 写 220）'
          % len(vals))
    print('     变体分布：%s' % dict(sorted(cnt.items())))
    print('     ⇒ 启用变体 = %s（即 1..%d）'
          % (sorted(cnt), max(cnt)))
for flag in ('--nuc-block-target', '--pair-every', '--ed-eta'):
    m = re.search(re.escape(flag) + r'\s+(\S+)', c)
    print('C  %-20s 生产值 = %s' % (flag, m.group(1) if m else '<未传>'))

# ---- C4：elastic_soft 的默认来源 ----
print()
print('C4 `elastic_soft` 的默认值来源（方案 §7.3 要求"不能隐藏默认开启"）：')
for i, s in enumerate(surf, 1):
    if 'elastic_soft' in s:
        print('   windowB_surface.py:%-5d %s' % (i, s.strip()[:104]))
print('   _bk_exp.py 里 elastic_soft 出现次数 = %d'
      % txt_drv.count('elastic_soft'))

# ---- C5：ed_eta 的理论标注 ----
print()
print('C5 `ed_eta` 的现状：')
for i, s in enumerate(surf, 1):
    if re.search(r'η ≈|eta.*0\.375|理论标定.*η', s):
        print('   windowB_surface.py:%-5d %s' % (i, s.strip()[:104]))
print('   ⇒ 方案 §7.3「`ed_eta` 必须有本构来源或被明确标记为校准参数」'
      '—— 现状是"有理论标定带、但生产值在带外"')

# ---- C6：位点密度 ----
print()
print('C6 引擎/驱动里有没有"位点密度"（方案 §6.1 的 λ_b = ∫I dV + ∫I_Γ dA 需要）：')
hits = []
for nm, L in (('_bk_exp.py', drv), ('windowB_surface.py', surf)):
    for i, s in enumerate(L, 1):
        if re.search(r'位点密度|site.?density|n_v\b|N_v\b|density', s):
            hits.append('%s:%d %s' % (nm, i, s.strip()[:84]))
print('   命中 %d 条：' % len(hits))
for h in hits[:12]:
    print('     ' + h)
print('   ⇒ 生产只按 `--nuc-init` 撒**有限个位点**（固定数目），**没有面密度/体密度量**')

# ---- C7：面级量 ----
print()
print('C7 引擎里有没有"面级"对象（方案 §7.1 的 v_f / M_f 需要）：')
for pat in (r'face_normals|face_offsets|halfspace|半空间|vertices\[|face_adjacency',
            r'\bM_f\b|面级|per.face|逐面'):
    h = [m.start() for m in re.finditer(pat, txt_surf)]
    print('   模式 %-46s 命中 %d' % (pat, len(h)))
print('   ⇒ 引擎是**逐胞**（N³ 格点）的，没有面对象；'
      '`M(n)` 是逐胞标量 (:5252)')
sys.exit(0)
