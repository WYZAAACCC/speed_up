#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_add_ref.py —— 把一篇 PDF 作为**正式文献记录**登记进索引，并抽取规范引用信息。

做四件事：
  1. 落到 `_litidx/refs.tsv`（file / DOI / journal / volume / pages / year / title / 本地全文路径）；
  2. 合并进 `_litidx/verdict2.tsv`（若已存在则补一列 `doi`，不覆盖既有判定）；
  3. 全文抽到 `_litidx/lit_txt/`（已抽则跳过）；
  4. 打印规范引用串。

用法: _t11_add_ref.py "<文件名或子串>" [--tag 备注]
"""
import csv
import os
import re
import sys

import pymupdf

PDFDIR = "/mnt/f/参考论文/马氏体仿真"
DST = "/mnt/f/speed_up/_litidx"
TXT = os.path.join(DST, "lit_txt")
REFS = os.path.join(DST, "refs.tsv")


def find_pdf(sub):
    """按**包含度**找（子串里有多少词命中文件名），再按相似度破平局。

    ⚠ 教训（本轮实测）：第一版用 `os.path.commonprefix` ⇒ 多篇都以后缀开头时
      会把**最短**的那篇选走（实测把 `A-correlative-approach-…-local-…` 选中）。
    """
    import difflib
    sub_l = sub.lower()
    words = [w for w in re.split(r"[^0-9a-zαβ′]+", sub_l) if len(w) > 2]
    cands = [f for f in sorted(os.listdir(PDFDIR))
             if f.lower().endswith(".pdf")]
    best, best_key = None, (-1, -1.0)
    for f in cands:
        fl = f.lower()
        hit = sum(1 for w in words if w in fl) / max(len(words), 1)
        ratio = difflib.SequenceMatcher(None, fl, sub_l).ratio()
        if (hit, ratio) > best_key:
            # 只在真有命中时才考虑
            best_key, best = (hit, ratio), f
    if best is None or best_key[0] <= 0:
        return None
    if best_key[0] < 1.0:
        print(f"⚠ 只有 {best_key[0]*100:.0f}% 的词命中文件名 ⇒ 选中：{best}")
    return best


def main() -> int:
    sub = sys.argv[1]
    tag = ""
    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]
    fn = find_pdf(sub)
    if fn is None:
        print(f"!! 没找到含 {sub!r} 的 PDF")
        return 1
    p = os.path.join(PDFDIR, fn)
    print(f"文件：{fn}")

    with pymupdf.open(p) as d:
        n = d.page_count
        pages = [d[i].get_text() for i in range(n)]
    full = "\n".join(pages)

    # ---- DOI ----
    dois = []
    for m in re.finditer(r"(?:https?://doi\.org/|doi:\s*|DOI:\s*)?(10\.\d{4,9}/[^\s,;)\]]+)",
                         full):
        t = m.group(1).rstrip(".")
        if t not in dois:
            dois.append(t)
    # ---- 期刊/卷页/年 ----
    jr = vol = pg = yr = ""
    m = re.search(r"(Acta Materialia|Computational Materials Science|"
                  r"Materials?\s*(?:&|and)\s*Design|Scripta Materialia|"
                  r"Materials Science and Engineering[ A-Z]*|"
                  r"Journal of Alloys and Compounds|"
                  r"Metallurgical and Materials Transactions[ A-Z]*|"
                  r"ISIJ International|Materials Letters|"
                  r"Modelling and Simulation in Materials Science and Engineering|"
                  r"International Journal of Plasticity)", full, re.I)
    if m:
        jr = m.group(1)
    m = re.search(r"\b(?:Vol\.?|Volume)\s*(\d{1,4})", full, re.I) or \
        re.search(rf"{re.escape(jr)}\s+(\d{{1,4}})\s*\(", full) if jr else None
    if m:
        vol = m.group(1)
    m = re.search(r"\b(20\d\d)\b", full)
    if m:
        yr = m.group(1)
    m = re.search(r"\bpp\.?\s*(\d{1,5}\s*[–\-−]\s*\d{1,5})", full)
    if m:
        pg = re.sub(r"\s+", "", m.group(1))

    # ---- 标题（首页第一个长行块）----
    title = ""
    try:
        with pymupdf.open(p) as d:
            dd = d[0].get_text("dict")
        spans = []
        for blk in dd.get("blocks", []):
            for line in blk.get("lines", []):
                t = "".join(sp.get("text", "") for sp in line.get("spans", []))
                t = re.sub(r"\s+", " ", t).strip()
                if len(t) >= 20:
                    sz = max((sp.get("size", 0) for sp in line.get("spans", [])), default=0)
                    spans.append((sz, blk.get("bbox", [0, 0, 0, 1])[1], t))
        if spans:
            spans.sort(key=lambda x: (-x[0], x[1]))
            top = spans[0][0]
            head = sorted([s for s in spans if s[0] >= top * 0.92], key=lambda x: x[1])[:3]
            title = " ".join(h[2] for h in head)
    except Exception:  # noqa: BLE001
        pass

    # ---- 落盘 ----
    os.makedirs(TXT, exist_ok=True)
    stem = re.sub(r"[^0-9A-Za-z._\u4e00-\u9fff-]+", "_", os.path.splitext(fn)[0])[:110]
    tp = os.path.join(TXT, stem + ".txt")
    if not os.path.exists(tp):
        with open(tp, "w", encoding="utf-8", errors="replace") as fh:
            fh.write(f"# SRC: {p}\n" + full)
        print(f"全文已抽 → {tp}")
    else:
        print(f"全文已存在 → {tp}")

    row = dict(file=fn, doi=dois[0] if dois else "", doi_all=";".join(dois),
               journal=jr, volume=vol, pages=pg, year=yr,
               title=title[:200], n_pages=n, local_txt=tp, tag=tag)
    new = not os.path.exists(REFS)
    with open(REFS, "a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row), delimiter="\t")
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"已登记 → {REFS}")

    # ---- 合并进 verdict2.tsv（补 doi 列，不动既有判定）----
    vp = os.path.join(DST, "verdict2.tsv")
    if os.path.exists(vp):
        with open(vp, encoding="utf-8") as fh:
            rd = list(csv.DictReader(fh, delimiter="\t"))
        cols = list(rd[0].keys()) if rd else []
        if "doi" not in cols:
            cols = cols + ["doi"]
        hit = False
        for r in rd:
            if r["file"] == fn:
                r["doi"] = row["doi"]
                hit = True
        if not hit:
            rd.append(dict(file=fn, category="KEEP", why="手工登记（用户后续加入）",
                           title=title[:200], doi=row["doi"]))
        with open(vp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t",
                               extrasaction="ignore")
            w.writeheader()
            for r in rd:
                w.writerow(r)
        print(f"verdict2.tsv {'已更新' if hit else '已追加'}（doi 列）")

    print("\n=== 规范引用 ===")
    print(f"  {title}")
    print(f"  {jr} {vol} ({yr}) {pg}" if jr else "  （期刊信息未在 PDF 内文出现）")
    print(f"  DOI: {row['doi'] or '（未找到）'}")
    for extra in dois[1:6]:
        print(f"  其他 DOI 候选: {extra}")
    print(f"  本地全文: {tp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
