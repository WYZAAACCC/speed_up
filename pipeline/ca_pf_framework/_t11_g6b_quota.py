#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_g6b_quota.py —— **G6-b 的决定性判据**：`natural` 的物理是否仍被 `--laths` 配额决定。

## 设计（`AGENTS.md` 教训 21：两臂只差一个因素）
  ⚠⚠ **第一版设计有缺陷，这里是修好的第二版**：
    第一版用 `1×14,2×14,…` vs `1..10` 重复 —— 那**同时改变了**：
      (a) 场号↔变体的映射（我想测的），**以及**
      (b) **种子位置** —— 因为 `_seed_next()` 按**场号**播种
          （`_bk_exp.py:1632` 用 `laths_eff[j-1]` 定轴、场号决定 `npref`）
    ⇒ 两臂的**采样位置不同** ⇒ **不是单因素对照**（实测：A 臂事件落在场 2..9，
      B 臂落在场 11,21,…,81）。
  ⇒ **第二版**：**只播前 `M0` 个场**（两臂**同样的场号序列**、**同样的位置**），
    只把**这些场的变体**换掉：

      臂 A:  前 10 场 = `1,2,3,4,5,6,7,8,9,10`   （每场一个不同变体）
      臂 B:  前 10 场 = `1,1,1,1,1,1,1,1,1,1`    （全部同一个变体）

    ⇒ **几何完全相同**（同一批场号、同一批位置、同样的 `_seed_next` 轨迹），
      **只差"这 10 个场里有哪些变体"**。
    ⚠ 两臂的**可及变体集合**不同（A 有 10 个、B 只有 1 个）——
      这正是要测的"配额"本身，**必须随结论说明**（不是纯顺序置换）。

## 判据（可 FAIL）
  * `natural` 模式的**总根数**与**实际变体分布**在两臂上的差异，
    应当**只反映"可及变体多少"这一条物理**，而**不该**出现
    "分布形状 == 配额形状"这类**由写出方式决定**的特征。
  * 本脚本只落**事实**（两臂的数），判定留给读的人 —— 避免我自己先入为主。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = "/root/miniconda3/envs/ml/bin/python"
OUT = "/mnt/f/speed_up/_exp/_bk_t5"
NV = 8
# ★★★ 决定性设计（`R623 §12.5`）：**两臂都恰好 2 个不同变体**（可及集合大小相同），
#   只换**是哪两个** ⇒ **单因素**（教训 21）。
#   若两臂的事件数与变体分布显著不同 ⇒ "哪些变体在场"确实由 `--laths` 决定
#   （`G6` 缺口成立）；若相同 ⇒ 配额表**不影响**物理（**撤案**）。
_AB_A = [1, 2, 1, 2, 1, 2, 1, 2]      # 变体 {1,2}
_AB_B = [1, 5, 1, 5, 1, 5, 1, 5]      # 变体 {1,5}
LATHS_A = ','.join(str(v) for v in _AB_A)
LATHS_B = ','.join(str(v) for v in _AB_B)

COMMON = [
    "--N", "64", "--dx-nm", "62.5", "--steps", "12", "--every", "1",
    "--snap-every", "99999", "--pair-every", "0", "--norm-smooth", "0",
    "--nthreads", "2", "--grow-stack", "--nuc-init", "4", "--nuc-every", "0",
    "--nuc-law", "athermal", "--nuc-block-target", "0",
    "--nuc-block-parallel", "1", "--nuc-supercrit", "1",
    "--nuc-sites-refill", "1", "--nuc-resample-ungated", "1",
    "--qs-clock", "1", "--alpha-km", "0.041739", "--T-end", "298",
    "--cool-rate", "2.3524e6", "--nuc-count-mode", "natural",
    "--per-field-axes", "1", "--nuc-order-by-drive", "1",
    "--out", OUT,
]


def run(tag, laths):
    cmd = [PY, "-u", "_bk_exp.py"] + COMMON + ["--laths", laths, "--tag", tag]
    log = "/mnt/f/speed_up/_w2_g6b_%s.log" % tag
    with open(log, "w") as fh:
        rc = subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


def summarize(tag):
    p = os.path.join(OUT, "dry_%s" % tag, "nuc_dbg.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    ev = d.get("T_events", []) or []
    hist = {}
    for e in ev:
        v = int(e.get("variant", -1))
        hist[v] = hist.get(v, 0) + 1
    return dict(n_events=len(ev), n_target=d.get("n_target_final"),
                hist=dict(sorted(hist.items())),
                modes=d.get("n_events_by_mode", {}))


def main():
    print("=" * 96)
    print("**两臂都恰好 2 个不同变体**（可及集合大小相同），**只换是哪两个** ")
    print(f"  臂 A（变体 {{1,2}}）: --laths {LATHS_A}")
    print(f"  臂 B（变体 {{1,5}}）: --laths {LATHS_B}")
    print("  ⇒ 变体数相同、几何相同、场号相同 ⇒ **单因素**")
    print("=" * 96)
    res = {}
    for tag, laths in (("g6bA", LATHS_A), ("g6bB", LATHS_B)):
        rc, log = run(tag, laths)
        print(f"\n[{tag}] 退出码={rc}  日志={log}")
        s = summarize(tag)
        res[tag] = s
        if s is None:
            print("   **没有 nuc_dbg.json** ⇒ 该臂作废")
            continue
        print(f"   事件数={s['n_events']}  末目标={s['n_target']}  模式={s['modes']}")
        print(f"   实际变体分布 = {s['hist']}")
        print(f"   落在几个变体上 = {len(s['hist'])}")
    print("\n" + "=" * 96)
    a, b = res.get("g6bA"), res.get("g6bB")
    if not a or not b:
        print("**无法判定**（某臂无产物）")
        return 1
    same_hist = (a["hist"] == b["hist"])
    same_n = (a["n_events"] == b["n_events"])
    print(f"事件数：A={a['n_events']}  B={b['n_events']}  ⇒ {'相同' if same_n else '不同'}")
    print(f"变体分布：{'**完全相同**' if same_hist else '**不同**'}")
    if same_hist and same_n:
        print("   ⇒ 换「哪两个变体」⇒ 结果**不变** ⇒ 配额表**不影响**物理"
              " ⇒ `G6` 缺口**不成立**（撤案）")
    else:
        print("   ⇒ 换「哪两个变体」⇒ 结果**变了** ⇒ **`G6` 缺口成立**"
              "（哪些变体在场由 `--laths` 决定）")
    print("   ⚠ 记账：本判据**固定「变体数 = 2」**，只测**是哪两个**。"
          "「变体数本身」的效应由 `R623 §12.3` 的实测单独记账（8 事件 → 0）。")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
