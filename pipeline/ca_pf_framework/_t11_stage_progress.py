#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_stage_progress.py —— 某算例**走到了第几档 / 什么温度**（判"是否被算力截断"）。

判据（可 FAIL）：若末态温度 **远高于 `T_end`**，则该算例的**每块根数**
被**步数预算**截断，而**不是**被物理律限制 ⇒ `C-2` 的 23 根/柱**从未有机会达到**。
"""
import csv
import os
import sys

sys.path.insert(0, ".")
import windowB_closure as CL  # noqa: E402

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
tag = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PRT2_b3_1005_1213"
d = next((os.path.join(b, tag) for b in BASES if os.path.isdir(os.path.join(b, tag))), None)
if d is None:
    sys.exit(f"找不到 {tag}")
rows = list(csv.DictReader(open(os.path.join(d, "series.csv"), encoding="utf-8")))
print(f"{tag}: series.csv 共 {len(rows)} 行")
if not rows:
    sys.exit(0)
print("列:", [k for k in rows[0].keys()][:12], "…")

# 找温度列（命名可能是 T / T_K / Tnow）
tcol = next((c for c in rows[0] if c.strip().lower() in ("t_k", "tnow", "temp", "tk")), None)
print(f"温度列 = {tcol!r}")

AKM = 0.041739
print("\n" + "=" * 88)
print("按 step 推断档号（引擎里档号就是「累计事件数」`k`）")
print("=" * 88)
print(f"{'step':>6} {'nslab_n':>8} {'Vt(um^3)':>10} {'k(档)':>7} {'T_k(K)':>9} {'剩余档':>7}")
for r in rows:
    try:
        st = int(float(r.get("step", 0)))
        ns = r.get("nslab_n", "")
        vt = float(r.get("Vt", "nan"))
        # Vt 在 CSV 里是 m^3（R581 P30 记账）⇒ 转 µm³
        vt_um = vt * 1e18 if vt == vt else float("nan")
        k = int(float(ns)) if str(ns).strip().isdigit() else None
        tk = CL.T_of_k(k, AKM) if k else float("nan")
        print(f"{st:>6} {str(ns):>8} {vt_um:>10.4f} {str(k):>7} {tk:>9.2f} "
              f"{(23 - k) if k else '':>7}")
    except (TypeError, ValueError) as e:
        print(f"  行解析失败: {e}")

print("\n★ 判读：末行的 `k`（= 该时刻的板条数）决定温度 `T_k = M_s − k/α`。")
print("  若 `T_k` **远高于** `T_end = 298 K` ⇒ 该跑**没走完冷却**，")
print("  每块根数被**步数预算**截断，`C-2` 的 23 根/柱**从未有机会达到**。")
print(f"  参照：走完全冷却需要 **{int(AKM * (CL.T_of_k(1, AKM) - 298))} 档**，")
print("  而 `--qs-max-relax 100` ⇒ 至少需要 **2200 步**。")
