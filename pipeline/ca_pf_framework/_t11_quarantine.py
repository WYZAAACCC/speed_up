#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_quarantine.py —— 把判定为「与当前工作无关」的论文**移走隔离**（不删除）。

纪律：
  * **移动，不删除** —— 目标目录带时间戳，可原样搬回；
  * **先做正/负对照**：移动前断言源存在、目标不存在；移动后断言源不存在、目标存在、**字节数一致**；
  * 先 `--dry-run` 打印将要移动什么，确认后再 `--apply`。

用法:
  _t11_quarantine.py --dry-run
  _t11_quarantine.py --apply
"""
import argparse
import os
import shutil
import sys

SRC = "/mnt/f/参考论文/马氏体仿真"
DST_ROOT = "/mnt/f/参考论文"
VERDICT = "/mnt/f/speed_up/_litidx/verdict2.tsv"

# 本轮隔离的类别（TBD 一律**不动**，留待人工复核）
MOVE_CATS = ("JUNK", "TEMPLATE")
TAG = "unrelated_20261005"


def load():
    rows = []
    with open(VERDICT, encoding="utf-8") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        for ln in fh:
            p = ln.rstrip("\n").split("\t")
            if len(p) >= len(hdr):
                rows.append(dict(zip(hdr, p)))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        ap.error("必须显式给 --dry-run 或 --apply")

    rows = load()
    todo = [r for r in rows if r["category"] in MOVE_CATS]
    keep = [r for r in rows if r["category"] == "KEEP"]
    tbd = [r for r in rows if r["category"] == "TBD"]
    print(f"源目录 {SRC}")
    print(f"  总 {len(rows)} 篇 | 将隔离 {len(todo)}（{'+'.join(MOVE_CATS)}）"
          f" | 保留 {len(keep)} | 待定（不动）{len(tbd)}")
    print(f"目标 {DST_ROOT}/{TAG}/")

    # ---- 负对照：源目录里这些文件必须都存在 ----
    missing = [r["file"] for r in todo if not os.path.exists(os.path.join(SRC, r["file"]))]
    if missing:
        print(f"!! 负对照失败：{len(missing)} 个待移动文件在源目录不存在，例如 {missing[:3]}")
        return 1
    print(f"对照① 源文件齐备 {len(todo)}/{len(todo)} ✅")

    if a.dry_run:
        for r in todo[:20]:
            print(f"  [DRY] {r['category']:8} {r['file']}")
        print(f"  ... 共 {len(todo)} 条（--apply 才真动）")
        return 0

    dst = os.path.join(DST_ROOT, TAG)
    os.makedirs(dst, exist_ok=True)
    assert os.path.isdir(dst), dst
    moved = failed = 0
    for i, r in enumerate(todo, 1):
        s = os.path.join(SRC, r["file"])
        d = os.path.join(dst, r["file"])
        if os.path.exists(d):
            print(f"  ! 目标已存在，跳过: {r['file']}")
            failed += 1
            continue
        sz0 = os.path.getsize(s)
        shutil.move(s, d)                      # 同一卷 ⇒ 元数据操作
        ok = (not os.path.exists(s)) and os.path.exists(d) and os.path.getsize(d) == sz0
        if ok:
            moved += 1
        else:
            failed += 1
            print(f"  !! 校验失败: {r['file']}")
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}  已移 {moved} 失败 {failed}", flush=True)

    left = len([f for f in os.listdir(SRC) if f.lower().endswith(".pdf")])
    print(f"\n=== 完成 === 移动 {moved}，失败 {failed}")
    print(f"源目录剩余 PDF {left}（应为 {len(rows)-moved}）")
    print(f"隔离目录 {dst}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
