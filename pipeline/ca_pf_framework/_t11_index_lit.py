#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_index_lit.py —— ⓪ 文献库索引 + 无关论文识别（450 PDF）。

关键设计（与第一版不同）：
  * **用字号抽标题**：首页里字号最大的那几行文字 = 标题。比"猜第 N 行"可靠得多。
  * **不做全文件 md5**（第一版在这上面走了 9p I/O，15 s/篇）。
  * 分类三分：JUNK（强无关）/ REL（明确相关）/ TBD（其余）。
  * **只输出清单，不移动、不删除任何文件。**

产出 F:/speed_up/_litidx/：
  index.tsv    file | pages | title | category | why
  review.txt   按 category 分组的人读清单
"""
import os
import re
import sys
import time
from collections import Counter

import pymupdf

SRC = "/mnt/f/参考论文/马氏体仿真"
DST = "/mnt/f/speed_up/_litidx"

JUNK = [
    # 生物 / 医学
    r"bioprint|biomaterial|biomedical|tissue engineer|scaffold|hydrogel|implant|dental|craniofacial",
    r"antibacterial|antimicrobial|bactericid|biocompat|cytotox|cell viabilit|osteogen|osteoblast",
    r"wound|drug delivery|anticancer|tumor|tumour|cancer|in vivo|in vitro|mouse|murine|zebrafish",
    r"protein|enzyme|peptide|\bDNA\b|\bRNA\b|gene |biofilm|chitosan|alginate|collagen|apatite",
    r"ludwigia|bioinspir|bio-inspired|bioinspired|bioactive glass|photosynth|plant |leaf|seed",
    r"agricultur|fertiliz|soil|wastewater|water treatment|desalinat|adsorption of|dye degradation",
    # 催化 / 电池 / 能源 / 电子
    r"electrocatal|photocatal|catalys|oxygen evolution|hydrogen evolution|\bORR\b|\bOER\b|\bHER\b",
    r"batter|lithium|li-ion|na-ion|anode|cathode|electrolyte|supercapacitor|fuel cell|solid oxide",
    r"solar cell|perovskit|photovoltaic|thermoelectric|piezoelectr|hydrogen storage|thermochemical",
    r"semiconductor|transistor|memristor|ferroelectr|superconduct|spintronic|topological",
    r"sensor|biosensor|humidity|wearable|flexible electronic|photodetector|light-emitting|\bLED\b",
    r"corrosion|coating|thin film|nanoparticle synthesis|drug|vaccine|antiviral|antifungal",
    r"polymer|epoxy|composite laminate|ceramic membrane|zeolite|metal-organic framework|\bMOF\b",
    r"magnetic propert|magnetocaloric|soft magnetic|permanent magnet|shape memory alloy",
]
REL = [
    r"martensit", r"Ti-?6Al-?4V|Ti6Al4V|Ti–6Al–4V|Ti 6Al 4V",
    r"\blath", r"\bpacket|\bblock\b|block size|block width", r"variant",
    r"nucleat", r"phase[- ]field", r"Burgers", r"habit plane", r"self[- ]accommodat",
    r"laser powder bed|LPBF|\bSLM\b|selective laser melt|additive manufactur|electron beam melt",
    r"cooling rate|cooling velocity", r"eigenstrain|misfit strain", r"dislocation",
    r"acicular|sympathetic|autocatal|Thermo-?Calc|CALPHAD|β transus|beta transus",
    r"austenite|ferrite|bainite|pearlite|carbon steel|low alloy steel|maraging",
    r"titanium alloy|zirconium|α′|α″|alpha prime|orthorhombic",
    r"microstructure (?:evolution|simulation)|grain growth|recrystalliz",
    r"residual stress|distortion|texture evolution|EBSD",
]
NOISE = re.compile(r"^(contents lists|journal homepage|available online|https?://|www\.|doi|"
                   r"received|accepted|published|©|\(c\)|elsevier|springer|wiley|mdpi|"
                   r"science ?direct|open access|this is an open|license|"
                   r"article|review article|research article|original|"
                   r"all rights reserved|issn|\d+\s*\(\d+\))", re.I)


def title_by_font(doc) -> str:
    """首页字号最大的文字块 ⇒ 标题。"""
    try:
        d = doc[0].get_text("dict")
    except Exception:  # noqa: BLE001
        return ""
    spans = []
    for blk in d.get("blocks", []):
        for line in blk.get("lines", []):
            txt = "".join(sp.get("text", "") for sp in line.get("spans", []))
            txt = re.sub(r"\s+", " ", txt).strip()
            if len(txt) < 12:
                continue
            size = max((sp.get("size", 0) for sp in line.get("spans", [])), default=0)
            spans.append((size, blk.get("bbox", [0, 0, 0, 1])[1], txt))
    if not spans:
        return ""
    spans.sort(key=lambda t: (-t[0], t[1]))
    top = spans[0][0]
    # 取与最大字号接近（≥0.92×）的前若干行，按纵坐标拼
    head = sorted([s for s in spans if s[0] >= top * 0.92], key=lambda t: t[1])[:4]
    out = " ".join(t[2] for t in head)
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) < 15 or NOISE.match(out):
        # 退路：取最靠前、长度合适的一行
        cand = [t[2] for t in sorted(spans, key=lambda t: t[1]) if len(t[2]) >= 20
                and not NOISE.match(t[2])]
        out = cand[0] if cand else out
    return out[:220]


def main() -> int:
    os.makedirs(DST, exist_ok=True)
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".pdf"))
    print(f"共 {len(files)} 个 PDF", flush=True)
    rows = []
    t0 = time.time()
    for i, fn in enumerate(files, 1):
        pages, title, err = -1, "", ""
        body = ""
        try:
            with pymupdf.open(os.path.join(SRC, fn)) as doc:
                pages = doc.page_count
                title = title_by_font(doc)
                body = doc[0].get_text()[:5000]
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        probe = (fn + " " + title + " " + body).lower()
        j = [p for p in JUNK if re.search(p, probe, re.I)]
        r = [p for p in REL if re.search(p, probe, re.I)]
        if j and not r:
            cat, why = "JUNK", ";".join(x[:26] for x in j[:3])
        elif r:
            cat, why = "REL", f"n_rel={len(r)}" + (";" + ";".join(x[:20] for x in j[:2]) if j else "")
        else:
            cat, why = "TBD", "no-signal"
        rows.append((fn, pages, title, cat, why, err))
        if i % 50 == 0:
            print(f"  {i}/{len(files)}  {time.time()-t0:.0f}s", flush=True)

    with open(os.path.join(DST, "index.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tpages\ttitle\tcategory\twhy\terr\n")
        for r in rows:
            fh.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
    with open(os.path.join(DST, "review.txt"), "w", encoding="utf-8") as fh:
        for cat in ("REL", "TBD", "JUNK"):
            sel = sorted([r for r in rows if r[3] == cat], key=lambda r: r[0].lower())
            fh.write(f"\n{'='*104}\n### {cat}  n={len(sel)}\n{'='*104}\n")
            for r in sel:
                fh.write(f"[{cat}] {r[0]}\n     T: {r[2]}\n     why: {r[4]}\n")
    c = Counter(r[3] for r in rows)
    print(f"\n用时 {time.time()-t0:.0f}s  === 分类汇总 === {dict(c)}")
    print(f"索引 {DST}/index.tsv ；清单 {DST}/review.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
