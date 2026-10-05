#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_t11_classify.py —— 文献库相关性分类（**只出清单，不动文件**）。

尺子（2026-10-05 用户拍板）：
  留：板条马氏体 / Ti-6Al-4V / 相场 / 形核 / 块与变体
      钢或其他合金的马氏体（机制同类）
      方法类（相场、水平集、FFT 微弹性、数值方法）
      增材制造 / 凝固 / 热历史
  移：生物医学、催化、电池、能量转换、光电磁功能材料、
      聚合物/复合材料、表面工程、传感（**非力学**）等

输入：_litidx/index.tsv（由 _t11_index_lit.py 产出，含标题）
输出：_litidx/verdict.tsv + verdict_review.txt
  verdict.tsv 列：file / category(KEEP|JUNK|TBD) / why / title
每个 PDF 的**首页文本**若已存在（_litidx/lit_txt），一并参与判定。
"""
import os
import re
import sys
from collections import Counter

DST = "/mnt/f/speed_up/_litidx"
IDX = os.path.join(DST, "index.tsv")

# ---------------- 无关（移走）----------------
JUNK = [
    # 生物 / 医学（含组织工程、植入体、药物）
    r"bioprint|biomaterial|biomedical|tissue engineer|scaffold|hydrogel|implant|dental|craniofacial",
    r"antibacterial|antimicrobial|bactericid|biocompat|cytotox|cell viabilit|osteogen|osteoblast|osteoimmun",
    r"wound|drug delivery|anticancer|tumou?r|cancer|in vivo|in vitro|mouse|murine|zebrafish|arthritis",
    r"cartilage|bone repair|calvarial|nerve regeneration|axonal|transdermal|skin repair|revasculariz",
    r"protein|enzyme|peptide|\bDNA\b|\bRNA\b|gene\b|biofilm|chitosan|alginate|collagen|apatite|exosome",
    r"ludwigia|bioinspir|bio-inspired|bioinspired|bioactive glass|photosynth|\bplant\b|\bleaf\b|\bseed\b",
    r"agricultur|fertiliz|\bsoil\b|wastewater|water treatment|desalinat|adsorption of|dye degradation",
    r"tetracycline|vancomycin|antibiotic|hemocompat|regenerative medicine",
    # 催化 / 电池 / 能量转换
    r"electrocatal|photocatal|\bcatalys|\bcatalyst|oxygen evolution|hydrogen evolution|\bORR\b|\bOER\b|\bHER\b",
    r"\bbatter|lithium|\bli-ion\b|\bna-ion\b|\banode\b|\bcathode\b|electrolyte|supercapacitor|fuel cell",
    r"solar cell|perovskite|photovoltaic|thermoelectric|piezoelectr|hydrogen storage|thermochemical",
    r"sodium-ion|zn-air|li-rich|li-s\b|solid oxide fuel",
    # 光 / 电 / 磁功能材料与器件
    r"luminescence|luminescent|phosphor|photochromic|\bLED\b|\bWLED|quantum dot|\bQDs?\b|upconversion",
    r"semiconductor|transistor|memristor|ferroelectr|superconduct|spintronic|topological insulator",
    r"magnetization dynamics|magnetocaloric|soft magnetic|permanent magnet|magnetic propert|multiferroic",
    r"photodetector|light-emitting|photoluminesc|band gap engineering|carrier mobility",
    # 聚合物 / 复合材料 / 表面工程 / 生物质
    r"\bpolymer\b|\bepoxy\b|polyamide|polyurethane|acrylic|hydrogel|composite laminate|\bDPD\b",
    r"biowaste|biomass|heteroatoms-doped carbon|carbon dots|nanofibrous|mesoporous silica",
    r"lubrication coating|anticorrosion|corrosion resistance|electroplating|electrodeposition",
    # 传感 / 可穿戴（非力学）
    r"biosensor|gas sensor|electrochemical sensor|humidity sensor|wearable|flexible sensor|strain sensor",
    # 其他明确无关
    r"metallic glass|bulk metallic glass|amorphous alloy|shape memory alloy|high-entropy alloy",
    r"additive friction stir|friction stir|welding of dissimilar|brazing|sintering of ceramic",
    r"concrete|cement|asphalt|wood|paper|textile|food|packaging",
]

# ---------------- 保留（相关）----------------
KEEP = [
    r"martensit", r"Ti-?6Al-?4V|Ti6Al4V|Ti–6Al–4V|Ti 6Al 4V",
    r"\blath", r"\bpacket\b|\bblock\b|block size|block width", r"\bvariant",
    r"nucleat", r"phase[- ]field", r"level[- ]set", r"Burgers", r"habit plane",
    r"self[- ]accommodat|self-accommodat|accommodation",
    r"laser powder bed|LPBF|\bSLM\b|selective laser melt|additive manufactur|electron beam melt|\bDED\b",
    r"cooling rate|cooling velocity|thermal history|solidification",
    r"eigenstrain|misfit strain|microelastic|FFT[- ]based|spectral method",
    r"dislocation|acicular|sympathetic|autocatal|Thermo-?Calc|CALPHAD|transus",
    r"austenite|ferrite|bainite|pearlite|carbon steel|low alloy steel|maraging|\bFe-C\b",
    r"titanium alloy|zirconium alloy|α′|α″|alpha prime|orthorhombic",
    r"microstructure (?:evolution|simulation)|grain growth|recrystalliz|precipitat",
    r"residual stress|distortion|texture evolution|\bEBSD\b|prior-?β|prior beta",
    r"steel", r"alloy design|strength.ductility|work harden",
]
NOISE = re.compile(r"^(volume|contents lists|journal homepage|available online|https?://|www\.|doi|"
                   r"received|accepted|published|©|\(c\)|elsevier|springer|wiley|mdpi|"
                   r"science ?direct|open access|this is an open|license|"
                   r"all rights reserved|issn|cover|editor)", re.I)


def strip_journal(t: str) -> str:
    return re.sub(r"^(materials? (&|and) design|acta materialia|journal of alloys and compounds|"
                  r"computational materials science|materials science and engineering[^ ]*|"
                  r"journal of materials [^ ]*|scripta materialia|metallurgical[^ ]*|"
                  r"international journal of [^:]{0,40}|nature communications|scientific reports|"
                  r"materials letters|journal of materials research|materials today[^ ]*)\s+", "", t, flags=re.I)


def main() -> int:
    rows = []
    with open(IDX, encoding="utf-8") as fh:
        hdr = fh.readline().rstrip("\n").split("\t")
        for ln in fh:
            p = ln.rstrip("\n").split("\t")
            if len(p) >= len(hdr):
                rows.append(dict(zip(hdr, p)))
    print(f"读入 {len(rows)} 条索引")

    out = []
    for r in rows:
        fn, title = r["file"], strip_journal(r.get("title", ""))
        # 首页文本（若已抽）
        safe = re.sub(r"[^0-9A-Za-z._\u4e00-\u9fff-]+", "_", os.path.splitext(fn)[0])[:110]
        tp = os.path.join(DST, "lit_txt", safe + ".txt")
        body = ""
        if os.path.exists(tp):
            try:
                with open(tp, encoding="utf-8", errors="replace") as f2:
                    body = f2.read()[:6000]
            except Exception:  # noqa: BLE001
                pass
        probe = (fn + " " + title + " " + body).lower()
        j = [p for p in JUNK if re.search(p, probe, re.I)]
        k = [p for p in KEEP if re.search(p, probe, re.I)]
        if k and not j:
            cat, why = "KEEP", f"keep={len(k)}"
        elif j and not k:
            cat, why = "JUNK", ";".join(x[:22] for x in j[:3])
        elif j and k:
            cat, why = "TBD", f"keep={len(k)}|junk={len(j)}: " + \
                ";".join(x[:16] for x in j[:2]) + " || " + ";".join(x[:16] for x in k[:2])
        else:
            cat, why = "TBD", "no-signal"
        out.append((fn, cat, why, title))

    with open(os.path.join(DST, "verdict.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\tcategory\twhy\ttitle\n")
        for r in out:
            fh.write("\t".join(str(x).replace("\t", " ") for x in r) + "\n")
    with open(os.path.join(DST, "verdict_review.txt"), "w", encoding="utf-8") as fh:
        for cat in ("KEEP", "TBD", "JUNK"):
            sel = sorted([r for r in out if r[1] == cat], key=lambda r: r[0].lower())
            fh.write(f"\n{'='*104}\n### {cat}  n={len(sel)}\n{'='*104}\n")
            for r in sel:
                fh.write(f"[{cat}] {r[0]}\n     T: {r[3]}\n     why: {r[2]}\n")
    print("=== 汇总 ===", dict(Counter(r[1] for r in out)))
    print("verdict.tsv / verdict_review.txt 已写出")
    return 0


if __name__ == "__main__":
    sys.exit(main())
