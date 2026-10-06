#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_lath_shape_when.py <tag> —— **逐场**量板条形状，定位"哪一根形状不对"。

判据：对每个场算面内椭圆的三轴跨度（沿该场自己的 a_ax / w_ax / n_hab），
      与"声明的板条几何 1000×500×510 nm（半轴 500/250/255）"对比。
"""
import glob
import os
import sys

import numpy as np

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD1"
d = next((os.path.join(b, TAG) for b in BASES
          if os.path.isdir(os.path.join(b, TAG))), None)
sns = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
print("=" * 96)
print("【%s】逐场板条形状（对照：声明几何 half = a 500 / w 250 / n 255 nm）" % TAG)
print("=" * 96)
for sp in sns:
    with np.load(sp, allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        N = reg.shape[0]
        a_ax = np.asarray(z['a_ax'], float) if 'a_ax' in z.files else None
        w_ax = np.asarray(z['w_ax'], float) if 'w_ax' in z.files else None
        n_hab = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
        vk = np.asarray(z['vmap_keys']) if 'vmap_keys' in z.files else None
        vv = np.asarray(z['vmap_vals']) if 'vmap_vals' in z.files else None
        step = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
    L = N * 62.5e-9
    print("\n快照 %s（step=%d）  盒 %.2f µm" % (os.path.basename(sp), step, L * 1e6))
    flds = sorted(int(v) for v in np.unique(reg) if v != 0)
    print("  非零场数 = %d %s" % (len(flds), flds[:12]))
    print("  %-6s %-8s %-8s %-9s %-9s %-9s %s"
          % ('场', '变体', '胞数', '沿a(nm)', '沿w(nm)', '沿n(nm)', '判读'))
    for k in flds[:14]:
        idx = np.argwhere(reg == k).astype(np.float64) * 62.5e-9
        var = int(vv[list(vk).index(k)]) if (vk is not None and k in list(vk)) else -1
        sp_a = sp_w = sp_n = float('nan')
        if a_ax is not None:
            # ⚠ numpy≥2.0 去掉了 ndarray.ptp() 方法 ⇒ 用 np.ptp()
            sp_a = float(np.ptp(idx @ a_ax))
            sp_w = float(np.ptp(idx @ w_ax))
            sp_n = float(np.ptp(idx @ n_hab))
        verd = ''
        if not np.isnan(sp_a):
            # 声明半长轴 500 nm ⇒ 全长 1000 nm
            r = sp_a / 1000e-9
            verd = ('≈声明(1000nm) %.2f×' % r) if 0.7 < r < 1.4 else \
                   ('**偏离声明 %.2f×**' % r)
        print("  %-6d %-8s %-8d %-9.0f %-9.0f %-9.0f %s"
              % (k, var, idx.shape[0], sp_a * 1e9, sp_w * 1e9, sp_n * 1e9, verd))
print("\n★ 读法：`沿a` = 该场沿其**长轴**的跨度（全长，应 ≈ 1000 nm = plate_L）")
