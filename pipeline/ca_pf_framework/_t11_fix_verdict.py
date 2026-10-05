#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_fix_verdict.py —— 清掉 `verdict2.tsv` 里一次匹配失败误加的记录。

留档：第一次跑 `_t11_add_ref.py` 时 `find_pdf` 用了 `os.path.commonprefix`，
把 `A-correlative-approach-…-local-…` 选成了目标，并往 `verdict2.tsv` 追加了一行。
本脚本按文件名前缀删除该行；并打印剩余行数与带 `doi` 的行数作自检。
"""
import csv
import os
import sys

P = "/mnt/f/speed_up/_litidx/verdict2.tsv"
BAD = "A-correlative-approach-to-evaluating-the-links"


def main() -> int:
    with open(P, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    cols = list(rows[0].keys())
    bad = [r for r in rows if r["file"].startswith(BAD)]
    for r in bad:
        print(f"删除: {r['file']}  | doi={r.get('doi', '')!r}")
    if not bad:
        print("（没有需要删除的行）")
    keep = [r for r in rows if not r["file"].startswith(BAD)]
    with open(P, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        for r in keep:
            w.writerow(r)
    print(f"剩余行数: {len(keep)}（原 {len(rows)}）")
    print(f"带 doi 的行: {sum(1 for r in keep if r.get('doi'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
