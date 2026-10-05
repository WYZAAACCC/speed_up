#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_meta_keys.py —— 读某算例 `meta.json` 的 `exp_args` 里指定的键（硬步骤 A）。

用法: _t11_meta_keys.py <tag> [key ...]
"""
import json
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
tag = sys.argv[1] if len(sys.argv) > 1 else "dry_t10B9"
keys = sys.argv[2:] or [
    "nuc_periodic_seed", "nuc_sites_refill", "nuc_resample_ungated",
    "nuc_block_target", "nuc_block_parallel", "nuc_init", "alpha_km",
    "qs_clock", "qs_max_relax", "nuc_law", "nuc_count_mode",
    "per_field_axes", "nuc_order_by_drive", "nuc_iface_nucleation",
    "nv", "N", "steps", "plate_L", "plate_W", "plate_T", "beta_h", "gamma0"]
d = next((os.path.join(b, tag) for b in BASES
          if os.path.exists(os.path.join(b, tag, "meta.json"))), None)
if d is None:
    sys.exit(f"**找不到 {tag}/meta.json**")
m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
ea = m.get("exp_args", {}) or {}
print(f"【{tag}】  {d}")
print(f"  （顶层键 {len(m)} 个；exp_args {len(ea)} 个）")
for k in keys:
    v = ea.get(k, m.get(k, "(缺)"))
    print(f"  {k:24} = {v!r}")
