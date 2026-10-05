#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_fix_verdict_doi.py —— 修 `verdict2.tsv` 里两篇关键文献的 `doi` 列（按精确文件名）。

留档：`_t11_add_ref.py` 的 upsert 只按 `file` 去重，但早期追加路径曾写入空 doi 行；
本脚本把两篇的 doi 写成确认值，并打印自检。
"""
import csv
import sys

P = "/mnt/f/speed_up/_litidx/verdict2.tsv"
FIX = {
    "Variant selection during α precipitation in Ti–6Al–4V under the influence of local stress – A simulation study.pdf":
        "10.1016/j.actamat.2013.06.042",
    "Effect of autocatalysis on variant selection of α precipitates during phase transformation in Ti-6Al-4V alloy.pdf":
        "10.1016/j.commatsci.2016.07.032",
}


def main() -> int:
    with open(P, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    cols = list(rows[0].keys())
    if "doi" not in cols:
        cols.append("doi")
    n = 0
    for r in rows:
        d = FIX.get(r["file"])
        if d and r.get("doi") != d:
            print(f"写入 doi: {r['file'][:60]}… -> {d}")
            r["doi"] = d
            n += 1
    with open(P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"共 {len(rows)} 行；改 {n} 行；带 doi 的行 = "
          f"{sum(1 for r in rows if r.get('doi'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
