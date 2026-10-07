#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_facet_cfg.py <tag> —— 从 meta.json 读**刻面/各向异性相关的全部开关**。

要回答的问题：生产配置里 `mob_wulff` / `mob_dip` / `facet_*` / `beta_*` / `band_cells`
到底各是什么值 ⇒ 判定"伸长的各向异性来自哪条通道"。
"""
import json
import os
import sys

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"
KEYS = ["beta_h", "beta_w", "mob_wulff", "mob_dip", "mob_iform", "mob_ratio",
        "facet_proj", "facet_lam", "facet_eps", "band_cells", "reinit_band",
        "adv", "adv_grad", "norm_smooth", "aniso", "nuc_shape", "eng_elong",
        "eng_r_nm", "eng_t_nm", "plate_L", "plate_W", "plate_T", "pair_aniso",
        "ed_pair", "eps0_mode", "rank1_swap", "gamma0"]
for tag in (sys.argv[1:] or ["c2B647"]):
    p = os.path.join(ROOT, "dry_%s" % tag, "meta.json")
    print("=" * 88)
    if not os.path.exists(p):
        print("【%s】无 meta.json" % tag)
        continue
    j = json.load(open(p, encoding="utf-8"))
    a = j.get("exp_args", {})
    print("【%s】" % tag)
    for k in KEYS:
        v = a.get(k, j.get(k, '—'))
        print("   %-14s = %r" % (k, v))
    # 打印所有含 facet/mob/wulff/dip/band 的键（防漏）
    print("   --- 所有相关键（模糊匹配）---")
    for src, nm in ((a, 'args'), (j, 'top')):
        for k, v in sorted(src.items()):
            if any(t in k.lower() for t in ("facet", "wulff", "dip", "band",
                                            "beta", "mob", "aniso")):
                print("   [%s] %-20s = %r" % (nm, k, v))
