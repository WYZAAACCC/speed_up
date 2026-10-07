#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_b2_abcmp.py —— 比 `dry_B2SM_pre` 与 `dry_B2SM_post` 的 CSV。

## 判据（`B2-D1` 登记的 J1）
* **两臂逐位相同** ⇒ ⛔ **`post` 没生效**（开关是死的）
* **两臂不同** ⇒ ✅ **生效了** ⇒ 再谈 `B2-D3` 的靶
"""
import csv
import os

ROOT = "/mnt/f/speed_up/pipeline/ca_pf_framework/_exp/_bk_block"
A = os.path.join(ROOT, "dry_B2SM_pre", "series.csv")
Bp = os.path.join(ROOT, "dry_B2SM_post", "series.csv")


def load(p):
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8") as fh:
        r = list(csv.DictReader(fh))
    return (list(r[0].keys()) if r else None), r


ka, ra = load(A)
kb, rb = load(Bp)
print("=" * 96)
print("B2 A/B：`dry_B2SM_pre` vs `dry_B2SM_post`")
print("=" * 96)
print("  pre  行数 = %s    post 行数 = %s" % (len(ra) if ra else None, len(rb) if rb else None))
if not ra or not rb:
    print("  ⛔ 缺 CSV")
    raise SystemExit(1)
print("  列名一致：%s" % (ka == kb))
n = min(len(ra), len(rb))
diff_cols = []
for c in ka:
    va = [ra[i].get(c) for i in range(n)]
    vb = [rb[i].get(c) for i in range(n)]
    if va != vb:
        diff_cols.append(c)
print("  前 %d 行里**不同的列**（%d 个）：" % (n, len(diff_cols)))
for c in diff_cols[:14]:
    print("     %-16s  pre=%s  post=%s" % (c, ra[n - 1].get(c), rb[n - 1].get(c)))
print()
print("  ⇒ 判定：%s" % ("✅ **两臂不同 ⇒ `post` 真的生效了**"
                       if diff_cols else
                       "⛔ **逐位相同 ⇒ `post` 没生效**（开关是死的，必须查）"))
