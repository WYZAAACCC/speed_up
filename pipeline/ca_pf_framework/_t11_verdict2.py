#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_verdict2.py —— 文献相关性判决（v2）：**标题 + 首页正文**。

为什么要 v2：v1 用的 `lit_txt` 只存了首末页且标题常被抽成页码（如 `80 (2014) 327–340`）
⇒ 189/211 落在 no-signal，判不了。

v2 做法：
  * 现抽首页正文（不落盘全文，只在内存里判），取标题 + 前 3000 字符；
  * **先剔模板页**（Cover / Editorial Board / Editors-for / 目录页）——这些是期刊附件，无学术内容；
  * 打分：无关信号 vs 相关信号，并**要求无关信号出现在标题或首段**（避免正文里偶然提到 battery 就误杀）。
输出 _litidx/verdict2.tsv + verdict2_review.txt（**仍不动任何文件**）。
"""
import os
import re
import sys
from collections import Counter

import pymupdf

SRC = "/mnt/f/参考论文/马氏体仿真"
DST = "/mnt/f/speed_up/_litidx"

# 模板/附件页（无学术内容）
TEMPLATE = re.compile(
    r"^(cover|editorial[- ]board|editors[- ]for|contents|table of contents|"
    r"front ?matter|back ?matter|masthead|index)", re.I)
TEMPLATE_TITLE = re.compile(
    r"(editor[- ]in[- ]chief|advisory editor|^volume \d+,|issn \d|editorial board)", re.I)

# 期刊名整行 —— 绝不能当标题（`guess_title` 漏判时会把它们选进来，实测 171/450）
JOURNAL_NAME = re.compile(
    r"^(journal of alloys and compounds|computational materials science|"
    r"acta materialia|materials? (&|and) design|scripta materialia|"
    r"materials science and engineering[ a-z]*|materials letters|"
    r"journal of materials (science|research|processing)[ a-z]*|"
    r"metallurgical and materials transactions[ a-z]*|"
    r"international journal of (plasticity|solids and structures|heat and mass transfer|"
    r"refractory metals[ a-z]*|mechanical sciences)|"
    r"nature (communications|materials)|scientific reports|"
    r"additive manufacturing|materials today[ a-z]*|"
    r"journal of the mechanics and physics of solids|"
    r"modelling and simulation in materials science and engineering|"
    r"computational materials science|"
    r"isij international|materials transactions|tetsu[- ]to[- ]hagane|"
    r"materials characterization|journal of nuclear materials|"
    r"physical review [a-z]+|applied physics letters|"
    r"surface and coatings technology|corrosion science|"
    r"journal of applied physics|ceramics international|"
    r"journal of the european ceramic society|intermetallics|"
    r"progress in materials science|annual review of materials research)"
    r"[\s:.,]*$", re.I)

JUNK = [
    (r"bioprint|biomaterial|biomedical|tissue engineer|scaffold|hydrogel|implant|dental|craniofacial|osteogen|osteoblast|osteoi|wound|drug delivery|anticancer|tumou?r|cancer|arthritis|cartilage|bone repair|calvarial|nerve regeneration|axonal|transdermal|skin repair|revasculariz|chitosan|alginate|collagen|apatite|exosome|antibacterial|antimicrobial|bactericid|biocompat|cytotox|antibiotic|vancomycin|tetracycline", "bio-med"),
    (r"electrocatal|photocatal|\bcatalys|\bcatalyst|oxygen evolution|hydrogen evolution|\bORR\b|\bOER\b|\bHER\b|fuel cell", "catalysis"),
    (r"\bbatter|lithium|\bli-ion\b|\bna-ion\b|\banode\b|\bcathode\b|electrolyte|supercapacitor|sodium-ion|zn-air|li-rich|li-s\b|zinc storage|solid oxide fuel", "battery"),
    (r"solar cell|perovskite|photovoltaic|thermoelectric|piezoelectr|hydrogen storage|thermochemical", "energy"),
    (r"luminescence|luminescent|phosphor|photochromic|\bLED\b|\bWLED|quantum dot|\bQDs?\b|upconversion|photoluminesc|optical propert|magnetostriction|magnetic tunab|magnetization dynamics|magnetocaloric|soft magnetic|permanent magnet|multiferroic|ferroelectr|superconduct|spintronic|topological insulator|semiconductor|transistor|memristor|photodetector|light-emitting|quantum well|band gap|carrier mobility|electronic.*magnetic and.*transport", "functional"),
    (r"\bpolymer\b|\bepoxy\b|polyamide|polyurethane|acrylic|composite laminate|\bDPD\b|biowaste|biomass|heteroatoms-doped|carbon dots|nanofibrous|mesoporous silica|copolymer|amphiphilic|metamaterial|auxetic|actuator", "polymer"),
    (r"lubrication coating|anticorrosion|corrosion resistance|electroplating|electrodeposition|in-reactor corrosion|thin film|ion beam assisted|magnetron sputt|black and reflective Al|cvd|chemical vapor deposition|reaxff|force field", "surface/dep"),
    (r"biosensor|gas sensor|electrochemical sensor|humidity sensor|wearable|flexible sensor|strain sensor|acoustic signal", "sensor"),
    (r"metallic glass|bulk metallic glass|amorphous alloy|amorphous gan|polyamorphism|shape memory alloy|high-entropy alloy|superalloy|inconel|nickel-based|grCop|heavy alloy|w-ni-fe|bi2o3|glass frit", "other-alloy"),
    (r"concrete|cement|asphalt|\bwood\b|paper|textile|\bfood\b|packaging|solder|thermally conductive|thermal conductivity", "other-mat"),
    (r"superalloy|inconel|\bSiC\b|\bGaN\b|\bGaAs\b|quantum wells|silicon carbide|\bSi\b layers|zirconium alloy|zr-nb|nuclear|irradiat", "other-sys"),
]
KEEP = [
    (r"martensit", "martensite"),
    (r"Ti-?6Al-?4V|Ti6Al4V|Ti–6Al–4V|Ti 6Al 4V", "Ti64"),
    (r"\blath", "lath"),
    (r"\bpacket\b|\bblock\b|block size|block width", "block/packet"),
    (r"\bvariant", "variant"),
    (r"nucleat|nucleation", "nucleation"),
    (r"phase[- ]field|level[- ]set|gibbs", "phase-field"),
    (r"Burgers|habit plane|self[- ]accommodat|accommodation|Kurdjumov|Sachs|orientation relationship", "crystallography"),
    (r"laser powder bed|LPBF|\bSLM\b|selective laser melt|additive manufactur|electron beam melt|\bDED\b|direct laser deposit", "AM"),
    (r"cooling rate|cooling velocity|thermal history|solidification|temperature field|thermal cycle", "thermal"),
    (r"eigenstrain|misfit strain|microelastic|FFT[- ]based|spectral method|elastic strain energy|variational", "mechanics"),
    (r"dislocation|acicular|sympathetic|autocatal|Thermo-?Calc|CALPHAD|transus", "micro-mech"),
    (r"austenite|ferrite|bainite|pearlite|carbon steel|low alloy steel|maraging", "steel"),
    (r"titanium alloy|zirconium alloy|α′|α″|alpha prime|orthorhombic|ω phase", "Ti-alloy"),
    (r"microstructure (?:evolution|simulation)|grain growth|recrystalliz|precipitat|grain refinement|texture evolution", "microstructure"),
    (r"residual stress|distortion|\bEBSD\b|prior-?β|prior beta|parent grain|misorientation", " microstructure2"),
]


def first_page(doc, n=3000):
    t = ""
    for p in range(min(2, doc.page_count)):
        try:
            t += doc[p].get_text()
        except Exception:  # noqa: BLE001
            pass
        if len(t) > n:
            break
    return t[:n]


def guess_title(txt):
    lines = [re.sub(r"\s+", " ", x).strip() for x in txt.splitlines()]
    lines = [x for x in lines if len(x) >= 18]
    best, bs = "", -1e9
    for i, ln in enumerate(lines[:20]):
        if re.match(r"^(contents lists|journal homepage|available online|https?://|www\.|doi|"
                    r"received|accepted|published|©|\(c\)|elsevier|springer|wiley|mdpi|"
                    r"science ?direct|open access|this is an open|license|all rights|issn)", ln, re.I):
            continue
        if JOURNAL_NAME.match(ln):          # ★ 期刊名整行绝不作为标题
            continue
        # 版权/开放获取声明行（实测会顶到标题位）
        if re.match(r"^\d{4}-\d{3,4}/©|©\s*\d{4}|the author\(s\)|published by elsevier|"
                    r"open access article under|creative commons|cc[- ]by", ln, re.I):
            continue
        # 期刊卷期页行，如 "Computational Materials Science 241 (2024) 113030"
        if re.search(r"\b(19|20)\d{2}\)\s*\d{3,6}\b", ln) or \
           re.match(r"^[A-Z][A-Za-z &.\-]{4,60}\s+\d{1,4}\s*\(\s*(19|20)\d{2}\s*\)", ln):
            continue
        # 作者/单位行（多逗号 + 上标数字 + 缩写名）
        if re.search(r"\b[A-Z]\.\s?[A-Z]?\.?\s?[A-Z][a-z]+,", ln) or \
           len(re.findall(r",", ln)) >= 4 or re.search(r"[a-z],[a-z]", ln):
            continue
        if re.match(r"^[\d\s.,;:()\-–—]+$", ln):
            continue
        letters = sum(c.isalpha() for c in ln)
        if letters < 12:
            continue
        s = -i + min(len(ln), 110) * 0.05
        s += 2.0 if letters / max(len(ln), 1) > 0.8 else 0
        s -= 3.0 if re.search(r"@|university|department|institute", ln, re.I) else 0
        if s > bs:
            best, bs = ln, s
    return best[:200]


def main() -> int:
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".pdf"))
    print(f"共 {len(files)} 个 PDF", flush=True)
    out = []
    for i, fn in enumerate(files, 1):
        title, head, err = "", "", ""
        try:
            with pymupdf.open(os.path.join(SRC, fn)) as doc:
                txt = first_page(doc)
            title = guess_title(txt)
            head = re.sub(r"\s+", " ", txt[:1500])
        except Exception as e:  # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        if TEMPLATE.match(fn) or TEMPLATE_TITLE.search(title) or TEMPLATE_TITLE.search(fn):
            out.append((fn, "TEMPLATE", "journal cover/editorial page", title))
            continue
        probe = (fn + " || " + title + " || " + head).lower()
        j = [(p, n) for p, n in JUNK if re.search(p, probe, re.I)]
        k = [(p, n) for p, n in KEEP if re.search(p, probe, re.I)]
        if k and not j:
            cat, why = "KEEP", "keep:" + ",".join(n for _, n in k[:4])
        elif j and not k:
            cat, why = "JUNK", "junk:" + ",".join(n for _, n in j[:3])
        elif j and k:
            cat, why = "TBD", ("keep:" + ",".join(n for _, n in k[:3]) + " | junk:"
                               + ",".join(n for _, n in j[:3]))
        else:
            cat, why = "TBD", "no-signal"
        out.append((fn, cat, why, title))
        if i % 50 == 0:
            print(f"  {i}/{len(files)}", flush=True)

    with open(os.path.join(DST, "verdict2.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tcategory\twhy\ttitle\n")
        for r in out:
            fh.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
    with open(os.path.join(DST, "verdict2_review.txt"), "w", encoding="utf-8") as fh:
        for cat in ("KEEP", "TBD", "JUNK", "TEMPLATE"):
            sel = sorted([r for r in out if r[1] == cat], key=lambda r: r[0].lower())
            fh.write(f"\n{'='*104}\n### {cat}  n={len(sel)}\n{'='*104}\n")
            for r in sel:
                fh.write(f"[{cat}] {r[0]}\n     T: {r[3]}\n     why: {r[2]}\n")
    print("=== 汇总 ===", dict(Counter(r[1] for r in out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
