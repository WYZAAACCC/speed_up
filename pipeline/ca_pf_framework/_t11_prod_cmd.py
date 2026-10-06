#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_prod_cmd.py —— 构造**生产配置**的 `_bk_exp.py` 命令（参数从 `t10B9` 的 `exp_args` 回读）。

## 为什么要它
  `_t5_short.py` 的 `SWITCHES` 是**写死的 13 项**，**没有透传口子** ⇒
  无法加 `--pf-phi onfly`（而它按 `AGENTS.md` 记账约能省 ~11 GB @N=160/nv=220）。
  `t10PROD1` 已因**内存看门狗**被杀（`VmHWM=20.18 GB > 20 GB 上限`）。
  ⇒ 直调 `_bk_exp.py`，参数**从生产算例自己的 `meta.json` 回读**（硬步骤 A）。

用法:
  _t11_prod_cmd.py --print                 # 只打印命令
  _t11_prod_cmd.py --run --tag X [覆盖...]  # 直接跑
"""
import argparse
import json
import os
import subprocess
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
PY = "/root/miniconda3/envs/ml/bin/python"
SRC = "dry_t10B9"          # 参数来源（生产算例）
ROOT = os.path.dirname(os.path.abspath(__file__))


def load_src():
    d = next((os.path.join(b, SRC) for b in BASES
              if os.path.exists(os.path.join(b, SRC, "meta.json"))), None)
    if d is None:
        sys.exit(f"**找不到 {SRC}/meta.json**")
    m = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    return m, (m.get("exp_args", {}) or {})


def build(over):
    m, ea = load_src()
    # ⚠ `laths` 在 meta.json 里是**字符串**（`a.laths` 被 json 原样存下，如 "1,1,2,2,…"），
    #   不是数组 ⇒ 先判类型再解析（我第一版按数组处理 ⇒ ValueError）。
    _l = ea.get("laths", m.get("laths"))
    if isinstance(_l, str):
        laths = [int(x) for x in _l.replace(' ', '').split(',') if x.strip()]
    elif _l:
        laths = [int(x) for x in _l]
    else:
        laths = []
    nv = int(ea.get("nv", m.get("nv", len(laths) or 220)))

    def g(k, dflt):
        v = over.get(k, ea.get(k, m.get(k, dflt)))
        return dflt if v is None else v

    cmd = [PY, "-u", "_bk_exp.py",
           "--N", str(g("N", 160)),
           "--dx-nm", str(g("dx_nm", 62.5)),
           "--steps", str(g("steps", 2400)),
           "--every", str(g("every", 20)),
           "--snap-every", str(g("snap_every", 200)),
           "--pair-every", str(g("pair_every", 100)),
           "--norm-smooth", str(g("norm_smooth", 0)),
           "--nthreads", str(g("nthreads", 4)),
           "--grow-stack",
           "--nuc-init", str(g("nuc_init", 6)),
           "--nuc-every", str(g("nuc_every", 0)),
           "--nuc-law", str(g("nuc_law", "athermal")),
           "--nuc-block-target", str(g("nuc_block_target", 9)),
           "--nuc-block-parallel", str(g("nuc_block_parallel", 1)),
           "--nuc-supercrit", str(g("nuc_supercrit", 1)),
           "--nuc-sites-refill", str(g("nuc_sites_refill", 1)),
           "--nuc-shape", str(g("nuc_shape", "ellipsoid")),
           "--nuc-occ-guard", str(g("nuc_occ_guard", 1)),
           "--nuc-periodic-seed", str(g("nuc_periodic_seed", 1)),
           "--nuc-overlap-nm", str(g("nuc_overlap_nm", 62.5)),
           "--eng-cadence", str(g("eng_cadence", 30)),
           "--qs-clock", str(g("qs_clock", 1)),
           "--qs-max-relax", str(g("qs_max_relax", 100)),
           "--alpha-km", repr(float(g("alpha_km", 0.041739))),
           "--T-end", repr(float(g("T_end", 298.0))),
           "--cool-rate", repr(float(g("cool_rate", 2352400.0))),
           "--plate-L", str(g("plate_L", 1000.0)),
           "--plate-W", str(g("plate_W", 500.0)),
           "--plate-T", str(g("plate_T", 510.0)),
           "--gamma0", str(g("gamma0", 0.25)),
           "--beta-h", str(g("beta_h", 6.477)),
           "--facet-proj", str(g("facet_proj", 0)),
           "--facet-excl", str(g("facet_excl", 0)),
           "--reinit-dt", repr(float(g("reinit_dt", 1e-4))),
           "--reinit-band", str(g("reinit_band", 6.0)),
           # ---- 本轮新增的开关（生产值 = 归档 ⇒ 逐位不变）----
           "--nuc-count-mode", str(g("nuc_count_mode", "manual")),
           "--per-field-axes", str(g("per_field_axes", 0)),
           "--nuc-order-by-drive", str(g("nuc_order_by_drive", 0)),
           "--nuc-iface-nucleation", str(g("nuc_iface_nucleation", 0)),
           "--nuc-resample-ungated", str(g("nuc_resample_ungated", 0)),
           # ---- 本轮要对比的两项 ----
           "--pf-phi", str(g("pf_phi", "materialized")),
           "--ckpt-every", str(g("ckpt_every", 0)),
           "--wrap-every", str(g("wrap_every", 0)),
           "--laths", (",".join(str(int(x)) for x in laths) if laths
                       else ",".join("1" for _ in range(nv))),
           "--out", str(g("out", "_exp/_bk_t5")),
           "--tag", str(g("tag", "t10PROD2"))]
    return cmd, nv, len(laths)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--print', dest='doprint', action='store_true')
    ap.add_argument('--tag', default='t10PROD2')
    ap.add_argument('--steps', type=int, default=None)
    ap.add_argument('--pf-phi', default=None)
    ap.add_argument('--ckpt-every', type=int, default=None)
    ap.add_argument('--mem-limit-gb', type=float, default=None)
    a = ap.parse_args()
    over = {k: v for k, v in (('steps', a.steps), ('pf_phi', a.pf_phi),
                              ('ckpt_every', a.ckpt_every)) if v is not None}
    over['tag'] = a.tag
    cmd, nv, nl = build(over)
    print(f"参数来源 = {SRC}/meta.json（回读）  nv={nv}  laths={nl} 个")
    print("\n命令：")
    print('  ' + ' '.join(cmd))
    if a.doprint or not a.run:
        sys.exit(0)
    log = "/mnt/f/speed_up/_w2_%s.log" % a.tag
    print(f"\n运行中 → {log}")
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    print(f"退出码 = {rc}")
    tail = subprocess.run(["tail", "-10", log], capture_output=True, text=True)
    print(tail.stdout)
