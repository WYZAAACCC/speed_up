#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_arch_cmp.py <tag> [...] —— 取归档算例的关键参数 + step0 种子形状（交叉核对用）。"""
import glob
import json
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
DX = 62.5e-9
tags = sys.argv[1:] or ["dry_t5AB_A", "dry_t5AB_B"]
for tag in tags:
    d = os.path.join(ROOT, tag)
    print("=" * 92)
    print("【%s】" % tag)
    mj = os.path.join(d, "meta.json")
    if os.path.exists(mj):
        j = json.load(open(mj, encoding="utf-8"))
        a = j.get("exp_args", j)
        for k in ("beta_h", "beta_h_used", "plate_L", "plate_W", "plate_T",
                  "eng_r_nm", "eng_elong", "eng_t_nm", "nuc_init", "nuc_law",
                  "grow_stack", "facet_proj", "mob_iform", "mob_ratio",
                  "steps", "arm", "N", "nv"):
            kk = k if k in a else k.replace('_', '-')
            if kk in a:
                print("   %-16s = %r" % (k, a[kk]))
    sns = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    print("   快照 %d 个：%s" % (len(sns), [os.path.basename(x) for x in sns[:4]]))
    if sns:
        with np.load(sns[-1], allow_pickle=False) as z:
            reg = np.asarray(z['region']).astype(np.int32)
            a_, w_, nh_ = (np.asarray(z[k], float) for k in ('a_ax', 'w_ax', 'n_hab'))
            st = int(np.asarray(z['step']).ravel()[0]) if 'step' in z.files else -1
        L = reg.shape[0] * DX
        flds = sorted(int(v) for v in np.unique(reg) if v != 0)
        print("   末快照 step=%d  盒 %.2f µm  场数 %d" % (st, L * 1e6, len(flds)))
        print("   %-5s %-8s %-9s %-9s %-9s %-7s %-7s %s"
              % ('场', '胞数', '沿a(nm)', '沿w(nm)', '沿n(nm)', 'L/W', 'L/T', '绕盒'))
        ars = []
        for k in flds[:8]:
            m = (reg == k)
            if m.sum() < 8:
                continue
            idx = np.argwhere(m).astype(np.float64) * DX
            sa, sw, sn = (float(np.ptp(idx @ a_)), float(np.ptp(idx @ w_)),
                          float(np.ptp(idx @ nh_)))
            # 长轴取三轴最大（无先验）
            trio = sorted([sa, sw, sn], reverse=True)
            print("   %-5d %-8d %-9.0f %-9.0f %-9.0f %-7.2f %-7.2f %s"
                  % (k, idx.shape[0], sa * 1e9, sw * 1e9, sn * 1e9,
                     trio[0] / max(trio[1], 1e-30), trio[0] / max(trio[2], 1e-30),
                     'WRAP' if trio[0] > 0.6 * L else ''))
            ars.append(trio[0] / max(trio[2], 1e-30))
        if ars:
            print("   ⇒ **长厚比 中位 = %.2f**（%d 个场）" % (float(np.median(ars)), len(ars)))
