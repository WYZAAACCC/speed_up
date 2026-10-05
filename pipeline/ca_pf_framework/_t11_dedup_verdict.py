#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_dedup_verdict.py —— `verdict2.tsv` 按 `file` 去重（保留信息最全的一行）。

背景（留档）：`_t11_add_ref.py` 早期是 **append** 语义 ⇒ 同一篇被登记两次，
`verdict2.tsv` 变成 451 行（应 450）。本脚本按 `file` 去重，
保留策略 = **非空字段数最多**的那行（并列时取靠后的，因为后写的是修正版）。
"""
import csv
import sys

P = "/mnt/f/speed_up/_litidx/verdict2.tsv"


def score(r):
    return sum(1 for v in r.values() if v not in (None, "", "nan"))


def main() -> int:
    with open(P, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    cols = list(rows[0].keys())
    best = {}
    order = []
    for r in rows:
        k = r["file"]
        if k not in best:
            best[k] = r
            order.append(k)
        elif score(r) >= score(best[k]):
            print(f"去重（保留后写）: {k[:70]}…  "
                  f"{score(best[k])} -> {score(r)} 非空字段")
            best[k] = r
        else:
            print(f"去重（保留先写）: {k[:70]}…")
    out = [best[k] for k in order]
    with open(P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow(r)
    print(f"\n原 {len(rows)} 行 → 去重后 {len(out)} 行")
    print(f"带 doi 的行 = {sum(1 for r in out if r.get('doi'))}")
    for r in out:
        if r.get("doi"):
            print(f"   {r['doi']:38} {r['file'][:66]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
