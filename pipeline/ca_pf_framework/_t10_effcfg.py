#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t10_effcfg.py --- ★ 硬步骤 A：从**算例自己的 meta.json / closure.json** 取"实际生效配置"

规矩（R612 硬步骤 A）：判断参数的"实际取值"，唯一权威是算例自己的 meta / banner 生效值，
不是 .sh 启动器、不是 CLI 默认、不是 add_argument 的 default（三层都可能被上层覆盖）。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAGS = sys.argv[1:] or ["t10PRT2_b3_1005_1213", "t10B9"]

# 关心的键（按 goal 的分层）
WANT = [
    # ⑦ 几何/边界
    "N", "dx_nm", "L_um", "box_um", "nv", "nvar", "m",
    # ⑥ 热力学/动力学
    "alpha_KM", "alpha_km", "M_S_TI64", "T0_TI64", "cool_rate", "q", "T_end",
    "T_start", "steps", "qs_clock", "qs_max_relax", "nuc_law", "burst_km",
    # ② 生长
    "gamma0", "beta_h", "beta_w", "ed_eta", "aniso", "facet_lam", "facet_eps",
    "facet_proj", "mob", "mob_beta", "norm_smooth", "adv",
    # ① 形核
    "nuc_shape", "plate_L", "plate_W", "plate_T", "eng_elong", "overlap_nm",
    "nuc_init", "nuc_sites_refill", "nuc_max_per_step", "nuc_fresh_every",
    "nuc_block_target", "B", "nuc_block_parallel", "nuc_occ_guard",
    "nuc_supercrit", "nuc_periodic_seed", "r_nuc_nm",
    # 其他
    "laths", "vmap", "tag", "engine_sha", "sha",
]

for tag in TAGS:
    d = os.path.join(HERE, "_exp/_bk_t5/dry_%s" % tag)
    print("=" * 78)
    print("算例 %s" % tag)
    print("=" * 78)
    if not os.path.isdir(d):
        print("  ❌ 目录不存在")
        continue
    for fn in ("meta.json", "closure.json"):
        p = os.path.join(d, fn)
        if not os.path.exists(p):
            print("  -- %s：不存在 --" % fn)
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                J = json.load(f)
        except Exception as e:
            print("  -- %s：读取失败 %s --" % (fn, e))
            continue
        print("\n  ── %s（共 %d 键）──" % (fn, len(J)))
        # 先按 WANT 打印
        hit = set()
        for k in WANT:
            if k in J:
                print("     %-22s = %s" % (k, J[k]))
                hit.add(k)
        # 其余键全打（避免"只看我想到的键"这个老毛病）
        rest = [k for k in sorted(J.keys()) if k not in hit]
        print("     ── 其余 %d 个键（全打，防漏）──" % len(rest))
        for k in rest:
            v = J[k]
            s = str(v)
            if len(s) > 70:
                s = s[:67] + "..."
            print("     %-22s = %s" % (k, s))
    print()
