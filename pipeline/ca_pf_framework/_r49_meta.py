#!/usr/bin/env python3
"""R49: 读 mb1s62 的 meta，确认 snapshot / phi 间隔，好判断何时有 >=3 快照"""
import json, sys, os
base = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_mb"
for arm in ("dry_mb1s62", "dry_mb1L", "dry_mb1Ls"):
    p = os.path.join(base, arm, "meta.json")
    if not os.path.exists(p):
        print(arm, "no meta"); continue
    m = json.load(open(p))
    keys = ["arm","N","dx_nm","L_nm","steps","snap_every","phi_every","phi_band_every",
            "phi_band_cells","nreg","laths","multi_block","block_gap_nm","var_rule",
            "nuc_init","dx","seed","beta_h","beta_w","t_phys_nm","plate_L","plate_W"]
    print("===", arm)
    for k in keys:
        if k in m:
            print("   %-16s %s" % (k, m[k]))
    # any other interval-ish keys
    for k, v in sorted(m.items()):
        if ("every" in k or "interv" in k or "snap" in k or "phi" in k) and k not in keys:
            print("   %-16s %s" % (k, v))
