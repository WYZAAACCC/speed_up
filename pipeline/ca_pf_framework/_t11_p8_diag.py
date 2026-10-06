#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_p8_diag.py —— ⑧ 的**根因决策树**（预登记：数据一到就能直接判定，不临时想）。

## 用户 ⑧ 的原文要求
> 「注意最终应该有的马氏体板条数量，最终应该有两百多的马氏体板条，小于等于 nv 数，
>   **如果最终的马氏体板条数量不够的话请你检查是形核或者生长的哪里出了问题**，并且进行解决。」

## 本脚本做什么
  按**已实测过的计数器语义**（`R623 §14.5` 的 `dbg` 表 + `R625 §4.6.2` 的块判据）
  把"根数不够"分成**形核侧**与**生长侧**，并**逐条给出可 FAIL 的路径**。

## 判据来源（都是本会话实测过的，不是猜）
  | 计数器 | 含义 | 出处 |
  |---|---|---|
  | `fresh_blocked` | `fresh` 通道被拒次数 | `R623 §14.5` |
  | `cov` | 覆盖守卫拒绝次数 | `R623 §14.5` |
  | `oob` / `exc` | 越界 / 抛错 | `R623 §14.5` |
  | `supercrit` / `sc_try` | 超临界探针 | `R623 §14.5` |
  | `sites_resampled_ungated` | 解卡重抽（`G5a`） | `R623 §14.1` |
  | `n_target_final` | 档目标 | `R623 §16.2` |
  | `nblk_sig` / `blk_laths` / `blk_span_nm` | 块结构 | `R625 §4.6` |
"""
import csv
import json
import os
import sys

BASES = ["/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_t5",
         "/mnt/f/speed_up/_exp/_bk_t5"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "dry_t10PROD1"
GOAL_LO, GOAL_HI = 200, 220        # ⑧ 的「两百多」，且 ≤ nv=220
B_TARGET = 9

d = next((os.path.join(b, TAG) for b in BASES
          if os.path.isdir(os.path.join(b, TAG))), None)
if d is None:
    sys.exit(f"**找不到 {TAG}**")
print("=" * 96)
print(f"⑧ 根因决策树 —— {TAG}")
print("=" * 96)

# ---- ① 块结构（series.csv）----
p = os.path.join(d, "series.csv")
rows = list(csv.DictReader(open(p, encoding="utf-8"))) if os.path.exists(p) else []
last = rows[-1] if rows else {}
ns_nu = last.get('nslab_nu', '')
print(f"\n① 块结构（series.csv，{len(rows)} 行）")
print(f"   末行 step={last.get('step')}  nblk_sig={last.get('nblk_sig')}  "
      f"blk_laths={last.get('blk_laths')!r}  blk_span_nm={last.get('blk_span_nm')!r}")
print(f"   nslab_nu={ns_nu!r}  nslab_n={last.get('nslab_n')!r}  Vt={last.get('Vt')!r}")

# ---- ② 形核计数器（nuc_dbg.json）----
q = os.path.join(d, "nuc_dbg.json")
dbg, nb = {}, {}
if os.path.exists(q):
    j = json.load(open(q, encoding="utf-8"))
    dbg = j.get("dbg", {}) or {}
    nb = j.get("n_events_by_mode", {}) or {}
print(f"\n② 形核计数器（nuc_dbg.json{'  ✅' if dbg else '  ⚠ 尚未写出（跑完才写）'}）")
for k in ("fresh_cand", "fresh_blocked", "fresh_covfail", "cov", "oob", "exc",
          "supercrit", "sc_try", "sites_resampled", "sites_resampled_ungated",
          "sites_refilled", "ok", "n_events", "attach_ok", "end_pref"):
    if k in dbg:
        print(f"   {k:24} = {dbg[k]}")
print(f"   n_events_by_mode = {nb}")

# ---- ③ 决策树（**预登记**）----
print("\n" + "=" * 96)
print("③ 决策树（**预登记**；数据到位后按此判定，不临时改口径）")
print("=" * 96)
print("""
  Q0. 总根数够吗？
      · 根数用 `Σ blk_laths`（或 `Vt/V_lath`，**两套体积都报**）；
        ⚠ **不得**只用 `nslab_n`（多块下结构性无效，且会多读 1.17–1.67×）。
      · 够（200–220）⇒ **⑧ 该项 PASS**，转去核其它监控项。
      · 不够 ⇒ 走 Q1。

  Q1. 形核侧还是生长侧？看**档目标是否达到**：
      · `n_events` ≥ `n_target_final`（档目标已达，事件放够了）
        ⇒ **生长侧**：每块根数上不去 ⇒ 查 Q2。
      · `n_events` < `n_target_final`（事件没放够）
        ⇒ **形核侧**：事件被拒 ⇒ 查 Q3。

  Q2. 生长侧细分（事件够但每块根数少）：
      · `blk_laths` 低 且 `blk_span_nm/(blk_laths−1) ≈ 312.5 nm`
        ⇒ 层间距对、就是**放不下更多层** ⇒ 查 **几何容量**
          （`R624 §6.3`：`α_KM·(T_阈−T_end)`；`ellipsoid` 给 9.42 根/块）
        ⇒ 与「C-2 预言 24 根」的差就是 `§6.3` 那条张力，**须用户裁定**（不擅自改）。
      · `blk_laths` 低 且层间距**明显 > 312.5 nm**
        ⇒ 层之间有空隙 ⇒ **attach 通道落位失败** ⇒ 查 `cov`/`oob`。

  Q3. 形核侧细分（事件放不够）：
      · `cov` 大            ⇒ **覆盖守卫拒绝**（母相被占满）⇒ 这是 `G2`/`cov` 守卫那条
                              （`R623 §14.3` 已证 `G2` 不足够 ⇒ 需查 `attach` 可达性）
      · `fresh_blocked` 大  ⇒ `fresh` 通道被拒 ⇒ 查待机位点是否用尽（`sites_refilled`）
      · `oob`/`exc` 大      ⇒ **越界**（`G7` 那条；生产 `periodic_seed=1` ⇒ 应已消失）
      · `sites_resampled_ungated` 大而 `ok` 不增
        ⇒ 解卡机制在跑但**无效** ⇒ `R623 §14.1` 的结论复现 ⇒ 根因在别处
      · `supercrit`/`sc_try` 大 ⇒ 驱动力判据在拒 ⇒ **物理参数问题**（非落位问题）

  Q4. 无论哪一支：**先证明判据有分辨力**（`R581 P43`）
      —— 若某个计数器为 0（该支从未被走到），**不得**据此下结论。
""")