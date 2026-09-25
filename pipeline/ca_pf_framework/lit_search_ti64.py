#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""T5.1 文献检索（Crossref + OpenAlex 公开 API）—— 只取"可追溯的题录+DOI"，数值一律标【待核对原文】。

用法: lit_search_ti64.py   （后台跑；输出 docs/LIT_SEARCH_HITS_Ti64.md）
"""
import io, json, time, urllib.parse, urllib.request

QUERIES = [
    ("液相线/固相线（DSC/DTA）", "Ti-6Al-4V liquidus solidus temperature DSC differential scanning calorimetry"),
    ("V 的分配系数 k_V（beta/liquid 或 beta/alpha）", "Ti-6Al-4V vanadium partition coefficient beta liquid solidification"),
    ("alpha-prime 板条宽（TEM）", "Ti-6Al-4V alpha prime martensite lath width TEM transmission electron microscopy"),
    ("alpha-prime 板条/集束（SEM/EBSD）", "Ti-6Al-4V martensite lath colony packet size EBSD SEM laser powder bed"),
    ("板条间 beta 纳米膜", "Ti-6Al-4V retained beta interlath film nanometer alpha prime decomposition"),
    ("晶界 alpha 膜厚度", "Ti-6Al-4V grain boundary alpha layer thickness prior beta"),
    ("LPBF Ti-6Al-4V 组织综述", "laser powder bed fusion Ti-6Al-4V microstructure prior beta grain alpha prime review"),
    ("alpha-prime 分解时间标度", "Ti-6Al-4V alpha prime decomposition kinetics heat treatment beta precipitation"),
]

def crossref(q, rows=6):
    u = "https://api.crossref.org/works?rows=%d&select=DOI,title,container-title,issued,type&query.bibliographic=%s" % (
        rows, urllib.parse.quote(q))
    req = urllib.request.Request(u, headers={"User-Agent": "ti64-lit-search/1.0 (mailto:research@example.org)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        j = json.loads(r.read().decode("utf-8", "ignore"))
    out = []
    for it in j.get("message", {}).get("items", []):
        t = (it.get("title") or [""])[0]
        jr = (it.get("container-title") or [""])[0]
        yr = (it.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
        if t:
            out.append((t, jr, yr, it.get("DOI", "")))
    return out

def openalex(q, rows=6):
    u = "https://api.openalex.org/works?per-page=%d&search=%s" % (rows, urllib.parse.quote(q))
    req = urllib.request.Request(u, headers={"User-Agent": "ti64-lit-search/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        j = json.loads(r.read().decode("utf-8", "ignore"))
    out = []
    for it in j.get("results", []):
        t = it.get("title") or ""
        jr = ((it.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        yr = it.get("publication_year")
        doi = (it.get("doi") or "").replace("https://doi.org/", "")
        if t:
            out.append((t, jr, yr, doi))
    return out

lines = [u"# Ti64 文献检索命中（T5.1，自动取自 Crossref + OpenAlex 公开 API）", u"",
         u"> ⚠ 本文件只给**可追溯的题录 + DOI**；**所有数值必须回原文核对**（`docs/LIT_SEARCH_BRIEF_Ti64_THERMO.md` §2.1 要求：DOI + 图/表号 + 原句）。",
         u"> 检索时间：见文件末。", u""]
for tag, q in QUERIES:
    lines.append(u"## %s" % tag)
    lines.append(u"**query**: `%s`" % q)
    try:
        hits = crossref(q)
        lines.append(u"**Crossref**：")
        for t, jr, yr, doi in hits:
            lines.append(u"- %s — *%s* (%s) · DOI: `%s`" % (t.strip(), jr.strip(), yr, doi))
    except Exception as e:
        lines.append(u"- Crossref 失败：%s" % str(e)[:120])
    try:
        hits = openalex(q)
        lines.append(u"**OpenAlex**：")
        for t, jr, yr, doi in hits:
            lines.append(u"- %s — *%s* (%s) · DOI: `%s`" % (t.strip(), jr.strip(), yr, doi))
    except Exception as e:
        lines.append(u"- OpenAlex 失败：%s" % str(e)[:120])
    lines.append(u"")
    time.sleep(1.0)
lines.append(u"检索完成时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"))
io.open("/mnt/f/speed_up/docs/LIT_SEARCH_HITS_Ti64.md", "w", encoding="utf-8").write(u"\n".join(lines))
print("wrote docs/LIT_SEARCH_HITS_Ti64.md ; 行数", len(lines))