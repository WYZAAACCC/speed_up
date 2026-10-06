#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_prod_check.py —— 生产跑的**诚实核对**（硬步骤 A/B）。

核对三件事：
  1. `meta.json` 的 `exp_args` **实际生效值**（唯一权威）；
  2. 我传的开关里**哪些没被接受/被改写**（如 `--pf-phi`）；
  3. `series.csv` 的行内容（判断"2 行"是 step 0/20 还是别的东西）。
"""
import csv
import json
import os
import sys

D = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5/dry_t10PROD1"
KEYS = ["pf_phi", "pf_phi_chunk", "every", "pair_every", "snap_every",
        "steps", "nv", "N", "nuc_periodic_seed", "nuc_block_target",
        "nuc_init", "nuc_block_parallel", "nuc_count_mode", "per_field_axes",
        "nuc_order_by_drive", "nuc_iface_nucleation", "nuc_resample_ungated",
        "ckpt_every", "wrap_every", "alpha_km", "qs_clock", "qs_max_relax",
        "nthreads", "periodic_seed", "tag", "out"]
m = json.load(open(os.path.join(D, "meta.json"), encoding="utf-8"))
ea = m.get("exp_args", {}) or {}
print("=" * 80)
print("① meta.json 的 exp_args（**实际生效值**，硬步骤 A）")
print("=" * 80)
for k in KEYS:
    print(f"  {k:26} = {ea.get(k, m.get(k, '(缺)'))!r}")
print(f"\n  exp_args 总键数 = {len(ea)}")

print("\n" + "=" * 80)
print("② series.csv 内容")
print("=" * 80)
p = os.path.join(D, "series.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8")))
print(f"  行数 = {len(rows)}")
for r in rows:
    print(f"    step={r.get('step')}  Vt={r.get('Vt')}  nslab_n={r.get('nslab_n')}  "
          f"wall_s={r.get('wall_s')}  nf3_col={r.get('nf3_col')}")
