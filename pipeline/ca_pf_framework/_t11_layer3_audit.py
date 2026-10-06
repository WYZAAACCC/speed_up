#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_layer3_audit.py —— ⑥ 层次③（代码实现层）的**独有串核对表**。

## 纪律（硬步骤 D）
  「任何『某机制已生效』必须给出**独有成功串**或运行期输出；给不出 ⇒ 只能写『存在，未验证』」。

## 本脚本做什么
  对**每一项本轮改动**，在指定的日志里找它的**独有串**，并如实报 命中/未命中。
  ⚠ **未命中本身不是失败**：默认关的开关本来就不该命中（那是"惰性"的证据）。
  判据是：**该命中的必须命中；不该命中的必须不命中**。

用法: _t11_layer3_audit.py
"""
import os
import re

LOGS = {
    "生产跑 t10PROD1": "/mnt/f/speed_up/_w2_t10PROD1.log",
    "回归 r30reg": "/mnt/f/speed_up/pipeline/ca_pf_framework/_w2_r30_regress_stdout.log",
    "g7ON": "/mnt/f/speed_up/_w2_g7ON.log",
    "ifaceON": "/mnt/f/speed_up/_w2_ifaceON.log",
    "r1inv": "/mnt/f/speed_up/_w2_r1inv.log",
    "f2L1": "/mnt/f/speed_up/_w2_f2L1.log",
}

# (项, 独有串正则, 该在哪出现, 期望)
ITEMS = [
    ("G1+G6 natural 模式",
     r"R623 natural 模式|natural 模式（--nuc-count-mode natural）",
     "只在传 --nuc-count-mode natural 时", "生产跑**不该**有（默认 manual）"),
    ("G6 第二步：次序由驱动力定",
     r"drive_pick|order.by.drive|s292 补投轮",
     "只在 --nuc-order-by-drive 1 或 burst-km 1 时", "生产跑**应有** s292（burst-km=1）"),
    ("G4 逐变体轴",
     r"per.field.axes|_variant_axes|逐变体轴",
     "只在 --per-field-axes 1 时", "生产跑**不该**有（默认 0）"),
    ("G3 逐变体长轴自检",
     r"G3 PASS|along·nrm|along_per_variant",
     "只在 --per-field-axes 1 时", "生产跑**不该**有"),
    ("G5a 解卡（去 n_fresh>0 门控）",
     r"sites_resampled_ungated",
     "只在 --nuc-resample-ungated 1 时（**且必须真的发生重抽**）",
     "生产跑**不该**有；`g7ON/ifaceON` **应有**"),
    ("G2 异变体界面形核",
     r"iface_ok|iface_pair|iface_samevar",
     "只在 --nuc-iface-nucleation 1 时", "生产跑**不该**有；`ifaceON` **应有**"),
    ("C-5 步数轴修正",
     r"C-5 步数轴修正|beta_h_floor|beta_h_min",
     "**无条件**（纯判据打印）", "生产跑**应有**"),
    ("②-8 绕盒监控接线",
     r"wrap_any|wrap_n|wrap_fields",
     "只在 --wrap-every > 0 时", "生产跑**不该**有（wrap-every=0）"),
    ("`§122` F2 配对（λ>0）",
     r"§122|f2_lam|f2_pair_gamma",
     "只在 --f2-pair-gamma > 0 时", "生产跑**不该**有；`f2L1` **应有**"),
    ("`G7` 越界落点记录（插桩）",
     r"oob_geom|oob_why|_oobcap",
     "`nuc_dbg.json` 里（不是日志串）", "见下（读 json）"),
]


def hits(log, pat):
    if not os.path.exists(log):
        return None
    n = 0
    try:
        for ln in open(log, encoding="utf-8", errors="replace"):
            if re.search(pat, ln):
                n += 1
    except OSError:
        return None
    return n


print("=" * 104)
print("⑥ 层次③ 独有串核对表（硬步骤 D：给不出独有串 ⇒ 只能写『存在，未验证』）")
print("=" * 104)
for nm, pat, where, expect in ITEMS:
    print(f"\n【{nm}】")
    print(f"   独有串 = {pat}")
    print(f"   应在   = {where}")
    print(f"   期望   = {expect}")
    line = "   实测   = "
    parts = []
    for tag, lg in LOGS.items():
        c = hits(lg, pat)
        parts.append(f"{tag}: {'(无日志)' if c is None else c}")
    print(line + " | ".join(parts))

print("\n" + "=" * 104)
print("★ `G7` 插桩的独立核对（读 `nuc_dbg.json`，不是日志）")
print("=" * 104)
import json
for tag in ("g7OFF", "g7ON", "ifaceON"):
    for base in ("/mnt/f/speed_up/_exp/_bk_t5",
                 "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5"):
        p = os.path.join(base, f"dry_{tag}", "nuc_dbg.json")
        if not os.path.exists(p):
            continue
        j = json.load(open(p, encoding="utf-8"))
        g, w = j.get("oob_geom"), j.get("oob_why")
        print(f"  [{tag}] oob_geom 条数={None if g is None else len(g)}  "
              f"oob_why={w!r}")
        break
