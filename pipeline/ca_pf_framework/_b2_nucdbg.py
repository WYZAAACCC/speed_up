#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_nucdbg.py <tag>... —— 并排比较各臂的**形核通道统计**（`nuc_dbg.json`）。

## 目的（`R704 §6` 的缺口①）
`R702 §3.2` 与 `R704 §4` 的机理解释都是**相关性 + 推理**。
本工具把 `nuc_dbg.json` 的关键计数**并排**，用于**否证或支持**那些解释。

## 看什么
* `n_eng_ev`（形核事件总数）与 `n_events_by_mode`（`attach` / `stack` / `fresh`）
* `dbg.att`（attach 尝试）、`dbg.oob`（越界）、`dbg.cov`（覆盖）、`dbg.nfsv_ok`
* **`nfsv_nofield`**（因"无新场"而未形核）
* `c_shift_max_dx`、`edge_gap_min_dx`
"""
import json
import os
import sys

ROOTS = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block",
         "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"]
KEYS = ["n_eng_ev", "n_athermal_ev", "n_target_final", "n_fresh_fallback_to_stack",
        "nfsv_nofield"]
DKEYS = ["att", "oob", "cov", "exc", "ok", "nocand", "nfsv_ok", "attach_ok",
         "n_events", "forced_reinit", "end_pref", "c_shift_max_dx", "edge_gap_min_dx"]

tags = sys.argv[1:] or ["B2P_q0", "B2P_pre", "CLIell", "CLIbig"]
data = {}
print("=" * 112)
print("形核通道统计并排（源：各臂 `nuc_dbg.json`）")
print("=" * 112)
for t in tags:
    p = None
    for r in ROOTS:
        q = os.path.join(r, "dry_%s" % t, "nuc_dbg.json")
        if os.path.exists(q):
            p = q
            break
    if not p:
        print("\n【%s】无 nuc_dbg.json" % t)
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as e:
        print("\n【%s】读失败 %s" % (t, e))
        continue
    data[t] = d
    print("\n【%s】" % t)
    print("  顶层：%s" % {k: d.get(k) for k in KEYS if k in d})
    print("  模式：%s" % d.get("n_events_by_mode", {}))
    print("  dbg ：%s" % {k: d.get("dbg", {}).get(k) for k in DKEYS
                          if k in d.get("dbg", {})})

# ---- 并排表 ----
print("\n" + "=" * 112)
print("关键量并排")
print("=" * 112)
rows = [("n_eng_ev", lambda d: d.get("n_eng_ev")),
        ("attach", lambda d: d.get("n_events_by_mode", {}).get("attach", 0)),
        ("stack", lambda d: d.get("n_events_by_mode", {}).get("stack", 0)),
        ("fresh", lambda d: d.get("n_events_by_mode", {}).get("fresh", 0)),
        ("dbg.att", lambda d: d.get("dbg", {}).get("att")),
        ("dbg.oob", lambda d: d.get("dbg", {}).get("oob")),
        ("dbg.cov", lambda d: d.get("dbg", {}).get("cov")),
        ("nfsv_nofield", lambda d: d.get("nfsv_nofield")),
        ("c_shift_max_dx", lambda d: d.get("dbg", {}).get("c_shift_max_dx")),
        ("end_pref", lambda d: d.get("dbg", {}).get("end_pref"))]
print("  %-16s" % "量" + "".join("  %-16s" % t for t in tags))
for name, fn in rows:
    line = "  %-16s" % name
    for t in tags:
        v = fn(data[t]) if t in data else None
        line += "  %-16s" % ("—" if v is None else
                             ("%.4g" % v if isinstance(v, float) else v))
    print(line)
