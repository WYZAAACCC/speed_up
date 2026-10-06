#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_elong_dose_check.py —— **直接量归档臂**，交叉核对"长宽比 6.55"这个二手读数。

## 为什么要它（`AGENTS.md` §3.3 教训 23）
  我在 `R625 §4.6.8` 里引了 `_t5_stop_old.sh:9-13` 的注释值（`elong=7 → 长宽比 6.55`）。
  那是**别人写的二手读数** ⇒ **必须从原始归档算例自己量一遍**。
  文档里的现成结论本身也可能是错的。

## 量具来源（**逐字复用 `_t5_ab_dose.sh:55-83` 的内联量具**，不自造第二个）
  · 每条场排除场 0；胞数 < 8 跳过；
  · 位置协方差 `eigh` → 主轴 `p0/p1`；`n_hat` 方向跨度 = 厚度；
  · `长宽比 = p0/p1`，`长厚比 = p0/t`；跨度为 `(max−min+1)·Δx`。
  ⚠ 归档 `dry_*/snap_*.npz` 的键：`region`、`n_hab`（若有）。
"""
import glob
import os
import sys

import numpy as np

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework"
DX = 62.5

# (标签, 归档目录, 该臂的 --eng-elong)
ARMS = [
    ("t5AB_B", "dry_t5AB_B", 3.75),
    ("t5AD_375", "dry_t5AD_375", 3.75),
    ("t5AD_500", "dry_t5AD_500", 5.0),
    ("t5AD_700", "dry_t5AD_700", 7.0),
    ("t5AD_1000", "dry_t5AD_1000", 10.0),
    ("t5AB_A", "dry_t5AB_A", None),
    ("t5AB_C", "dry_t5AB_C", None),
    ("t5AB_D", "dry_t5AB_D", None),
]

print("=" * 104)
print("`--eng-elong` 剂量-响应的**原始归档复核**（量具逐字复用 `_t5_ab_dose.sh:55-83`）")
print("=" * 104)
print("  %-11s %-9s %-6s %-9s %-30s %s"
      % ('臂', 'elong', '场数', '末步', '长宽比 中位 [范围]', '长厚比 中位 [范围]'))
print("  " + "-" * 100)
rows = []
for tag, sub, el in ARMS:
    d = os.path.join(ROOT, "_exp", "_bk_t5", sub)
    sn = sorted(glob.glob(os.path.join(d, "snap_*.npz")))
    if not sn:
        print("  %-11s %-9s （无快照：%s 不存在或为空）" % (tag, el, sub))
        continue
    with np.load(sn[-1], allow_pickle=False) as z:
        reg = np.asarray(z['region']).astype(np.int32)
        nh = np.asarray(z['n_hab'], float) if 'n_hab' in z.files else None
    ar, lt = [], []
    for k in sorted(int(x) for x in np.unique(reg) if x != 0):
        idx = np.argwhere(reg == k).astype(np.float64)
        if idx.shape[0] < 8:
            continue
        c = idx - idx.mean(0)
        w, v = np.linalg.eigh(c.T @ c)
        o = np.argsort(w)[::-1]
        p = [float((c @ v[:, j]).max() - (c @ v[:, j]).min() + 1) * DX / 1000.0
             for j in o[:2]]
        if nh is not None:
            ax = nh / (np.linalg.norm(nh) + 1e-300)
            t = float((c @ ax).max() - (c @ ax).min() + 1) * DX / 1000.0
        else:
            t = float((c @ v[:, o[2]]).max() - (c @ v[:, o[2]]).min() + 1) * DX / 1000.0
        ar.append(p[0] / max(p[1], 1e-9))
        lt.append(p[0] / max(t, 1e-9))
    if not ar:
        print("  %-11s %-9s （无有效场）" % (tag, el))
        continue
    step = os.path.basename(sn[-1]).replace('snap_', '').replace('.npz', '')
    print("  %-11s %-9s %-6d %-9s %6.2f [%5.2f, %6.2f]%9s %6.2f [%5.2f, %6.2f]"
          % (tag, el, len(ar), step, np.median(ar), min(ar), max(ar), '',
             np.median(lt), min(lt), max(lt)))
    rows.append((tag, el, np.median(ar)))

print("\n" + "=" * 104)
print("★ 判读")
print("=" * 104)
ok = [(t, e, m) for t, e, m in rows if e is not None]
if len(ok) >= 3:
    ok.sort(key=lambda x: x[1])
    print("  剂量-响应（按 elong 升序）：")
    for t, e, m in ok:
        print("    elong=%-6s → 长宽比中位 %.2f   (%s)" % (e, m, t))
    mono = all(ok[i][2] <= ok[i + 1][2] + 1e-9 for i in range(len(ok) - 1))
    print("  判据「单调上升」：%s" % ('✅ PASS' if mono else '❌ FAIL'))
    print("  ⚠ 与 `_t5_stop_old.sh` 注释值对比：注释称 3.75→~3.5 / 5→4.75 / 7→6.55 / 10→7.32")
    print("    ⇒ 若本次实测与之**不一致**，说明注释里的数是另一个步点或另一批算例。")
else:
    print("  ⚠ 不足 3 个带 elong 标的臂 ⇒ **无法判定**（分辨力不足，不得下结论）")